[![Build Status](https://travis-ci.org/alphagov/notifications-admin.svg)](https://travis-ci.org/alphagov/notifications-admin)
[![Requirements Status](https://requires.io/github/alphagov/notifications-admin/requirements.svg?branch=master)](https://requires.io/github/alphagov/notifications-admin/requirements/?branch=master)


# notifications-admin

GOV.UK Notify admin application.

## Features of this application

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## First-time setup

Languages needed
- Python 3
- [Node](http://nodejs.org/) 5.0.0 or greater
```shell
    brew install node
```

[NPM](npmjs.org) is Node's package management tool. `n` is a tool for managing
different versions of Node. The following installs `n` and uses the latest
version of Node.
```shell
    npm install -g n
    n latest
    npm rebuild node-sass
```

The app runs within a virtual environment. To [install virtualenv](https://virtualenv.readthedocs.org/en/latest/installation.html), run
```shell
    [sudo] pip install virtualenv
```

Make a virtual environment for this app:
```shell
    mkvirtualenv -p /usr/local/bin/python3 notifications-admin
```

Install dependencies and build the frontend assets:
```shell
    ./scripts/bootstrap.sh
```

## Rebuilding the frontend assets

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

Then visit [localhost:6012](http://localhost:6012)
