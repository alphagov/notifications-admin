import os
from flask.ext.script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db


application = create_app(os.getenv('NOTIFICATIONS_ADMIN_ENVIRONMENT') or 'development')
manager = Manager(application)
port = int(os.environ.get('PORT', 6012))
manager.add_command("runserver", Server(host='0.0.0.0', port=port))
migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)


@manager.command
def list_routes():
    """List URLs of all application routes."""
    for rule in sorted(application.url_map.iter_rules(), key=lambda r: r.rule):
        print("{:10} {}".format(", ".join(rule.methods - set(['OPTIONS', 'HEAD'])), rule.rule))


if __name__ == '__main__':
    manager.run()
