#!/bin/bash

if [ "$1" == "web" ]
then
  exec opentelemetry-instrument \
    --traces_exporter otlp,console \
    --metrics_exporter otlp,console \
    --service_name admin \
  gunicorn --error-logfile - -c /home/vcap/app/gunicorn_config.py application

elif [ "$1" == "web-local" ]
then
  npm run build
  exec flask run --host 0.0.0.0 --port $PORT

else
  echo "Running custom command"
  exec $@
fi
