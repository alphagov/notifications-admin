from flask import render_template
from flask_login import login_required
from app.main import main


@main.route("/services")
@login_required
def choose_service():
    return render_template('views/choose-service.html')
