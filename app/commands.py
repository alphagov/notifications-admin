import click
from flask import current_app
from flask.cli import with_appcontext


@click.command('list-routes')
@with_appcontext
def list_routes():
    """List URLs of all application routes."""
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        print("{:10} {}".format(", ".join(rule.methods - set(['OPTIONS', 'HEAD'])), rule.rule))  # noqa


@click.command()
@click.argument('csv_path')
@with_appcontext
def tmp_backfill_areas(csv_path, dry_run=True):
    import csv

    from app.models.broadcast_message import BroadcastMessage

    for id, service_id in csv.reader(open(csv_path)):
        message = BroadcastMessage.from_id(id, service_id=service_id)
        print(f'Updating {message.id}')  # noqa

        if not dry_run:
            message._update_areas(force_override=True)


def setup_commands(application):
    application.cli.add_command(list_routes)
    application.cli.add_command(tmp_backfill_areas)
