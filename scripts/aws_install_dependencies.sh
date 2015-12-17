#!/bin/bash

echo "Install dependencies"
cd /home/ubuntu/notifications-admin;
gem install sass;
python app.py db upgrade
pip install -r /home/ubuntu/notifications-admin/requirements.txt
