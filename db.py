from credstash import getAllSecrets
from flask.ext.script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db

secrets = getAllSecrets(region="eu-west-1")

application = create_app('live')

for key in application.config.keys():
        if key in secrets:
                application.config[key] = secrets[key]


manager = Manager(application)
migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)
