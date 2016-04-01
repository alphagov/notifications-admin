from credstash import getAllSecrets
import os

default_env_file = '/home/notify-app/environment'
environment = 'live'

if os.path.isfile(default_env_file):
    with open(default_env_file, 'r') as environment_file:
        environment = environment_file.readline().strip()


# on aws get secrets and export to env
os.environ.update(getAllSecrets(region="eu-west-1"))

from config import configs

os.environ['NOTIFY_ADMIN_ENVIRONMENT'] = configs[environment]

from app import create_app

application = create_app()

if __name__ == "__main__":
        application.run()
