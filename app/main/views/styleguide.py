from flask import render_template
from app.main import main


@main.route('/_styleguide')
def styleguide():
    return render_template('views/styleguide.html')
