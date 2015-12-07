#!/bin/bash

echo "Install dependencies"
export FLASK_CONFIG=/home/ubuntu/config.cfg
python app.py db upgrade
pip install -r /home/ubuntu/notifications-admin/requirements.txt
