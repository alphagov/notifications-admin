from flask.ext.script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db

application = create_app('live')

manager = Manager(application)
migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)
