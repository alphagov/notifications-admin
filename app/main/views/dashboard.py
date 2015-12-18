from flask import render_template

from app.main import main

from ._jobs import jobs


@main.route("/dashboard")
def dashboard():
    return render_template(
        'views/dashboard.html',
        jobs=jobs,
        free_text_messages_remaining=560,
        spent_this_month='0.00'
    )
