#!/bin/bash

if [ "$1" == "web" ]
then
  gunicorn --error-logfile - -c /home/vcap/app/gunicorn_config.py application

elif [ "$1" == "web-local" ]
then
  flask run --host 0.0.0.0 --port $PORT

else
  echo -e "'\033[31m'FATAL: missing argument'\033[0m'" && exit 1
  exit 1

fi
