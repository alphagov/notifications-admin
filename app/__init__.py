from flask import Flask


def create_app():
    application = Flask(__name__)

    # application.config['NOTIFY_API_ENVIRONMENT'] = config_name
    # application.config.from_object(configs[config_name])
    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    return application

