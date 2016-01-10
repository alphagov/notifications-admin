from app import create_app
import os
from credstash import getAllSecrets
from flask.ext.script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db

secrets = getAllSecrets(region="eu-west-1")

application = create_app(os.getenv('NOTIFICATIONS_ADMIN_ENVIRONMENT') or 'live')

for key in application.config.keys():
        if key in secrets:
                application.config[key] = secrets[key]


manager = Manager(application)
migrate = Migrate(application, db)
manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
        application.run()
