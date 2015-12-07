#!/bin/bash

echo "Starting application"
export NOTIFICATIONS_ADMIN_ENVIRONMENT='live'
cd ~/notifications-admin/; 
sudo service notifications-admin start