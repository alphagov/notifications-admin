#!/bin/bash

if [ "$1" == "web" ]
then
  export OTEL_SERVICE_NAME=admin
  exec gunicorn --error-logfile - -c /home/vcap/app/gunicorn_config.py application

elif [ "$1" == "web-local" ]
then
  npm run build
  exec flask run --host 0.0.0.0 --port $PORT

else
  echo "Running custom command"
  exec $@
fi
