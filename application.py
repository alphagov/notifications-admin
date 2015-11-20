from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():
    return 'Hello from notifications-admin'

if __name__ == '__main__':
    app.run(port=6012)
