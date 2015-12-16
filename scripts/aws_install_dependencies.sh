#!/bin/bash

echo "Install dependencies"
cd /home/ubuntu/notifications-api; gem install sass
export FLASK_CONFIG=/home/ubuntu/config.cfg
python app.py db upgrade
pip install -r /home/ubuntu/notifications-admin/requirements.txt
