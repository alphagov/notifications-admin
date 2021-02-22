# notifications-admin

GOV.UK Notify admin application - https://www.notifications.service.gov.uk/

## Features of this application

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## Setting up

### Make sure you're using correct language versions

Languages needed
- Python 3.6.x

Need to install node? Run:

```shell
brew install node
```

#### `n` For Node version management

[NPM](npmjs.org) is Node's package management tool. `n` is a tool for managing
different versions of Node. The following installs `n` and uses the long term support (LTS)
version of Node.

```shell
npm install -g n
n lts
```

### Install Python dependencies

Install dependencies and build the frontend assets:

```shell
make bootstrap
```

### Create a local `environment.sh` file

In the root directory of the application, run:

```
echo "
export NOTIFY_ENVIRONMENT='development'
export FLASK_APP=application.py
export FLASK_ENV=development
export WERKZEUG_DEBUG_PIN=off
"> environment.sh
```

### AWS credentials

To run parts of the app, such as uploading letters, you will need appropriate AWS credentials. See the [Wiki](https://github.com/alphagov/notifications-manuals/wiki/aws-accounts#how-to-set-up-local-development) for more details.

### Running the application

In the root directory of the application, run:

```shell
make run-flask
```

Then visit [localhost:6012](http://localhost:6012)

## Updating application dependencies

`requirements.txt` file is generated from the `requirements-app.txt` in order to pin
versions of all nested dependencies. If `requirements-app.txt` has been changed (or
we want to update the unpinned nested dependencies) `requirements.txt` should be
regenerated with

```
make freeze-requirements
```

`requirements.txt` should be committed alongside `requirements-app.txt` changes.


## Automatically rebuild the frontend assets

If you want the front end assets to re-compile on changes, leave this running
in a separate terminal from the app

```shell
    npm run watch
```

## Working with static assets

When running locally static assets are served by Flask at http://localhost:6012/static/…

When running on preview, staging and production there’s a bit more to it:

![notify-static-after](https://user-images.githubusercontent.com/355079/50343595-6ea5de80-051f-11e9-85cf-2c20eb3cdefa.png)
