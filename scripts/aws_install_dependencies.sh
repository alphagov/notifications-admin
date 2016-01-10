#!/bin/bash

echo "Install dependencies"
cd /home/ubuntu/notifications-admin;
export FLASK_CONFIG=/home/ubuntu/config.cfg
pip3 install -r /home/ubuntu/notifications-admin/requirements.txt
python3 wsgi.py db upgrade
