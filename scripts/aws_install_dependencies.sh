#!/bin/bash

echo "Install dependencies"
cd /home/ubuntu/notifications-admin;
export FLASK_CONFIG=/home/ubuntu/config.cfg
python3 app.py db upgrade
pip3 install -r /home/ubuntu/notifications-admin/requirements.txt
