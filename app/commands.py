import click
from flask import current_app
from flask.cli import with_appcontext


@click.command('list-routes')
@with_appcontext
def list_routes():
    """List URLs of all application routes."""
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        print("{:10} {}".format(", ".join(rule.methods - set(['OPTIONS', 'HEAD'])), rule.rule))  # noqa


def setup_commands(application):
    application.cli.add_command(list_routes)
