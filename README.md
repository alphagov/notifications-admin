# notifications-admin

GOV.UK Notify admin application.

## Features of this application

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## First-time setup

### 1. Install Homebrew

Brew is a package manager for OSX. The following command installs brew:

```shell
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

This command changes occasionally. You can find the most recent command at [Homebrew](https://brew.sh)


### 2. Make Sure You're Using Correct Language Versions

Languages needed
- Python 3.6.x
- [Node](https://nodejs.org/) 10.15.3 or greater
- [npm](https://www.npmjs.com/) 6.4.1 or greater

Need to get node? Run:

```shell
    brew install node
```

#### 2.1. `n` For Node Version Management

[NPM](npmjs.org) is Node's package management tool. `n` is a tool for managing
different versions of Node. The following installs `n` and uses the long term support (LTS)
version of Node.

```shell
    npm install -g n
    n lts
```

#### 2.2. `nvm` For Node Version Management

NVM is also a popular tool for node verison managmement. Install it with Homebrew (instructions can be found with a simple Google search), and make sure you have a Node version installed higher than 10.15.3, and use it. I have arbitrarily chosen version `12.16.2` for this example.

```shell
    nvm use 12.16.2
```

### 3. Install NPM Dependencies

```shell
    npm install
    npm rebuild node-sass
```

### 4. Install `virtualenvwrapper`

You'll need the `pip` package [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html) installed. Installation is pretty easy; run this command for the 3.6.x version of Python you're using for this project:

```shell
    pip install virtualenvwrapper
```

...However, you'll need to configure it to run in your `bash` terminal. Add the following lines to your `~/.bash_profile` **if** you're using `pyenv` to manage your python versions:

*Note: Python version 3.6.3 is the 3.6.x version arbitrarily chosen for this example.*

```bash
    export WORKON_HOME=~/virtualenvs
    export VIRTUALENVWRAPPER_HOOK_DIR=$WORKON_HOME/hooks
    source ~/.pyenv/versions/3.6.3/bin/virtualenvwrapper.sh
```

If no `~/virtualenvs` directory exists, make one.

If you're using the main system Python version on an OSX machine, your final `~/.bash_profile` line will look more like this:

```bash
    source /usr/local/bin/virtualenvwrapper.sh
```

Please see the [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/index.html) website for more installation and configuration info. This step gives you access to `mkvirtualenv` on the command line.


### 5. Setup Virtual Environment

The app runs within a virtual environment. We use `mkvirtualenv` for easier working with `venvs`

**Using Your Machine's System Python:**

```shell
    mkvirtualenv -p /usr/local/bin/python3 notifications-admin
```

**Using pyenv:**

*Note: Python version 3.6.3 is the 3.6.x version arbitrarily chosen for this example.*

```shell
mkvirtualenv -p ~/.pyenv/versions/3.6.3/bin/python notifications-admin
```

### 6. Install Python Dependencies

Install dependencies and build the frontend assets:

```shell
    workon notifications-admin
    ./scripts/bootstrap.sh
```

**Note:** You may need versions of both Python 3 and Python 2 accessible to build the python dependencies. `pyenv` is great for that, and making both Python versions accessible can be done like so:

```shell
    pyenv global 3.6.3 2.7.15
```

### 7. Rebuilding the frontend assets

If you want the front end assets to re-compile on changes, leave this running
in a separate terminal from the app

```shell
    npm run watch
```

### 8. Create a local `environment.sh` file containing the following:

```
echo "
export NOTIFY_ENVIRONMENT='development'
export FLASK_APP=application.py
export FLASK_DEBUG=1
export WERKZEUG_DEBUG_PIN=off
"> environment.sh
```

### 9. AWS credentials

Your aws credentials should be stored in a folder located at `~/.aws`. Follow [Amazon's instructions](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-config-files) for storing them correctly


### 10. Running the application

In the root directory of the application, run:

```shell
    workon notifications-admin
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


## Working with static assets

When running locally static assets are served by Flask at http://localhost:6012/static/…

When running on preview, staging and production there’s a bit more to it:

![notify-static-after](https://user-images.githubusercontent.com/355079/50343595-6ea5de80-051f-11e9-85cf-2c20eb3cdefa.png)
