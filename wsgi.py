from app import create_app
import os
from credstash import getAllSecrets

secrets = getAllSecrets(region="eu-west-1")

application = create_app(os.getenv('NOTIFICATIONS_ADMIN_ENVIRONMENT') or 'live')

for key in application.config.keys():
        if key in secrets:
                application.config[key] = secrets[key]

if __name__ == "__main__":
        application.run()
