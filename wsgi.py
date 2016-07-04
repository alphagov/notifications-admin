from credstash import getAllSecrets
import os

# on aws get secrets and export to env
os.environ.update(getAllSecrets(region="eu-west-1"))

from app import create_app  # noqa

application = create_app()

if __name__ == "__main__":
        application.run()
