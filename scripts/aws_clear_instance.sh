#!/bin/bash

echo "Removing application and dependencies"

if [ -d "/home/notify-app/notifications-admin" ]; then
    # Remove and re-create the directory
    rm -rf /home/notify-app/notifications-admin
    mkdir -p /home/notify-app/notifications-admin
fi

