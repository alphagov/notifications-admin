import functools
import json
import os
import sys

import click
import flask
from flask import current_app


@click.group(name="command", help="Additional commands")
def command_group():
    pass


class notify_command:
    def __init__(self, name=None):
        self.name = name

    def __call__(self, func):
        decorators = [
            functools.wraps(func),  # carry through function name, docstrings, etc.
            click.command(name=self.name),  # turn it into a click.Command
        ]

        # in the test environment the app context is already provided and having
        # another will lead to the test db connection being closed prematurely
        if os.getenv("NOTIFY_ENVIRONMENT", "") != "test":
            # with_appcontext ensures the config is loaded, db connected, etc.
            decorators.insert(0, flask.cli.with_appcontext)

        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        for decorator in decorators:
            # this syntax is equivalent to e.g. "@flask.cli.with_appcontext"
            wrapper = decorator(wrapper)

        command_group.add_command(wrapper)
        return wrapper


def setup_commands(application):
    application.cli.add_command(command_group)


@notify_command(name="save-app-routes")
@click.option(
    "--acknowledge-removed-routes",
    is_flag=True,
    default=False,
)
def save_app_routes_command(acknowledge_removed_routes: bool):
    try:
        num_routes = save_app_routes(acknowledge_removed_routes=acknowledge_removed_routes)
        click.echo(f"Updated tests/route-list.json with {num_routes} routes.")
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)


def save_app_routes(acknowledge_removed_routes: bool) -> int:
    """
    Creates or updates a file containing a list of all of the routes served by the admin app.

    By default, this command will fail if any routes have been removed. The flag `acknowledge_removed_routes` can be
    used to force the new route list to be saved to disk.

    This powers a test that nudges us when routes are removed in case we should set up appropriate redirects.
    """
    current_routes = {r.rule for r in current_app.url_map.iter_rules()}
    with open("tests/route-list.json") as infile:
        expected_routes = set(json.load(infile))

    if acknowledge_removed_routes is False:
        removed_routes = expected_routes.difference(current_routes)
        if removed_routes:
            raise ValueError(
                "\nSome routes have been removed:\n"
                + "\n".join(f" -> {path}" for path in removed_routes)
                + "\n\n"
                + "Make sure there are appropriate redirects in place, "
                + "and then run `flask command save-app-routes --acknowledge-removed-routes`."
            )

    sorted_current_routes = sorted(list(current_routes))
    with open("tests/route-list.json", "w") as outfile:
        outfile.write(json.dumps(sorted_current_routes, indent=4) + "\n")

    return len(sorted_current_routes)
