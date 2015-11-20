from app.main import main


@main.route('/index')
def index():
    return 'Hello from notifications-admin'

