from flask import render_template
from app.main import main


@main.route("/user-profile")
def userprofile():
    return render_template('views/user-profile.html')
