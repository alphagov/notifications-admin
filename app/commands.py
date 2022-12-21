import functools
import json
import os

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
def save_app_routes():
    """
    Creates or updates a file containing a list of all of the routes served by the admin app.

    This powers a test that nudges us when routes are added/removed in case we need/want to set up appropriate
    redirects.
    """
    current_routes = {r.rule for r in current_app.url_map.iter_rules()}
    sorted_current_routes = sorted(list(current_routes))
    with open("tests/route-list.json", "w") as outfile:
        outfile.write(json.dumps(sorted_current_routes, indent=4) + "\n")

    current_app.logger.info(f"Updated tests/route-list.json with {len(sorted_current_routes)} routes.")
