[![Build Status](https://travis-ci.org/alphagov/notifications-admin.svg)](https://travis-ci.org/alphagov/notifications-admin)
[![Requirements Status](https://requires.io/github/alphagov/notifications-admin/requirements.svg?branch=master)](https://requires.io/github/alphagov/notifications-admin/requirements/?branch=master)


# notifications-admin

Application to handle the admin functions of the notifications application.

## Features of this application

 - Register users
 - Register services
 - Download CSV for an email or SMS batch
 - Show history of notifications
 - Reports

## First-time setup

You need [Node](http://nodejs.org/) which will also get you [NPM](npmjs.org),
Node's package management tool.
```shell
    brew install node
```

n is a tool for managing different versions of node. The following installs n
and uses the latest version of node.
```shell
    npm install -g n
    n latest
    npm rebuild node-sass
```

The frontend dependencies are managed using NPM and Bower. To install or update
*all the things*, run
```shell
    npm install
    npm run build
```

The app runs within a virtual environment. To [install virtualenv](https://virtualenv.readthedocs.org/en/latest/installation.html), run
```shell
    [sudo] pip install virtualenv
```

To make a virtualenv for this app, run
```shell
    mkvirtualenv -p /usr/local/bin/python3 notifications-admin
    pip install -r requirements.txt
    ./scripts/bootstrap.sh
```

## Building the frontend

If you want the front end assets to re-compile on changes, leave this running
in a separate terminal from the app
```shell
    npm run watch
```

## Running the application

```shell
    workon notifications-admin
    ./scripts/run_app.sh
```

Then visit [localhost:6012](localhost:6012)

## Domain model

All the domain models are defined in the
[models.py](https://github.com/alphagov/notifications-admin/blob/master/app/models.py)
file.
