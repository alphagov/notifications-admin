#!/bin/bash

echo "Removing application and dependencies"

if [ -d "/home/notify-app/notifications-admin" ]; then
    # Remove and re-create the directory
    rm -rf /home/notify-app/notifications-admin
    mkdir -vp /home/notify-app/notifications-admin
    # Remove installed py3 packages
    pip3 freeze | xargs pip3 uninstall -y
else
    echo "Directory does not exist, something went wrong!"
fi

