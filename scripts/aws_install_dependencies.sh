#!/bin/bash

echo "Install dependencies"
cd /home/notify-app/notifications-admin;
pip3 install --find-links=wheelhouse -r /home/notify-app/notifications-admin/requirements.txt
