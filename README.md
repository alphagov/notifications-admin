# notifications-admin

GOV.UK Notify admin application - https://www.notifications.service.gov.uk/

## Features of this application

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## First-time setup

### 1. Install Homebrew

Install [Homebrew](https://brew.sh), a package manager for OSX:

```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
```

### 2. Make sure you're using correct language versions

Languages needed
- Python 3.6.x
- [Node](https://nodejs.org/) 10.15.3 or greater
- [npm](https://www.npmjs.com/) 6.4.1 or greater

Need to install node? Run:

```shell
brew install node
```

#### 2.1. `pyenv` For Python version management

[pyenv](https://github.com/pyenv/pyenv) is a program to manage and swap between different versions of Python. To install:

```shell
brew install pyenv
```

And then follow the further installation instructions in https://github.com/pyenv/pyenv#installation to configure it.

#### 2.2. `n` For Node version management

[NPM](npmjs.org) is Node's package management tool. `n` is a tool for managing
different versions of Node. The following installs `n` and uses the long term support (LTS)
version of Node.

```shell
npm install -g n
n lts
```

### 3. Install NPM dependencies

```shell
npm install
npm rebuild node-sass
```

### 4. Install and use `virtualenvwrapper` (optional)

We suggest using a virtualenv to separate the python dependencies for this project from python dependencies for other projects.

Install [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html):

```shell
pip install virtualenvwrapper
```

Then follow the [virtualenvwrapper installation instructions](https://virtualenvwrapper.readthedocs.io/en/latest/install.html) docs to configure virtualenvwrapper for your terminal.

Set up your virtualenv:

```shell
mkvirtualenv notifications-admin
```

If you need to specify a certain version of python you can do this using `-p`, for example:

```shell
mkvirtualenv -p ~/.pyenv/versions/3.6.3/bin/python notifications-admin
```

Activate your virtualenv:

```shell
workon notifications-admin
```

### 5. Install Python dependencies

Install dependencies and build the frontend assets:

```shell
./scripts/bootstrap.sh
```

**Note:** You may need versions of both Python 3 and Python 2 accessible to build the python dependencies. `pyenv` is great for that, and making both Python versions accessible can be done like so:

```shell
pyenv global 3.6.3 2.7.15
```

### 6. Create a local `environment.sh` file containing the following:

```
echo "
export NOTIFY_ENVIRONMENT='development'
export FLASK_APP=application.py
export FLASK_DEBUG=1
export WERKZEUG_DEBUG_PIN=off
"> environment.sh
```

### 7. AWS credentials

Your aws credentials should be stored in a folder located at `~/.aws`. Follow [Amazon's instructions](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-config-files) for storing them correctly


### 8. Running the application

In the root directory of the application, run:

```shell
./scripts/run_app.sh
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
