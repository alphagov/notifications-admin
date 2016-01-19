#!/bin/bash

echo "Install dependencies"
cd /home/ubuntu/notifications-admin;
pip3 install -r /home/ubuntu/notifications-admin/requirements.txt
python3 db.py db upgrade
