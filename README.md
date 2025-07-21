# notifications-admin

GOV.UK Notify admin application - https://www.notifications.service.gov.uk/

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## Setting up

### Python version

At the moment we run Python 3.11 in production.

### NodeJS & NPM

If you don't have NodeJS on your system, install it with homebrew.

```shell
brew install node
```

`nvm` is a tool for managing different versions of NodeJS. Follow [the guidance on nvm's github repository](https://github.com/nvm-sh/nvm#installing-and-updating) to install it.

Once installed, run the following to switch to the version of NodeJS for this project. If you don't
have that version, it should tell you how to install it.

```shell
nvm use
```

### `environment.sh`

In the root directory of the application, run:

```
echo "
export NOTIFY_ENVIRONMENT='development'
export FLASK_APP=application.py
export FLASK_DEBUG=1
export WERKZEUG_DEBUG_PIN=off
"> environment.sh
```

### AWS credentials

To run parts of the app, such as uploading letters, you will need appropriate AWS credentials. See the [Wiki](https://github.com/alphagov/notifications-manuals/wiki/aws-accounts#how-to-set-up-local-development) for more details.

### uv

We use [uv](https://github.com/astral-sh/uv) for Python dependency management. Follow the [install instructions](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Pre-commit

We use [pre-commit](https://pre-commit.com/) to ensure that committed code meets basic standards for formatting, and will make basic fixes for you to save time and aggravation.

Install pre-commit system-wide with, eg `brew install pre-commit`. Then, install the hooks in this repository with `pre-commit install --install-hooks`.

## To run the application

```shell
# install dependencies, etc.
make bootstrap

# run the web app
make run-flask
```

Then visit [localhost:6012](http://localhost:6012).

Any Python code changes you make should be picked up automatically in development. If you're developing JavaScript or CSS code, run `make watch-frontend` to achieve the same.

## To test the application

```
# install dependencies, etc.
make bootstrap

# run all the tests
make test

# run the js tests
npx jest

# run a single js test
npx jest <pathToAJavascriptTestfile>

# continuously run js tests
npm run test-watch

# debug a js test in chrome
npm run debug --test=[name of test file]
```

To run a specific JavaScript test, you'll need to copy the full command from `package.json`.

## Further docs

- [Working with static assets](docs/static-assets.md)
- [JavaScript documentation](https://github.com/alphagov/notifications-manuals/wiki/JavaScript-Documentation)
- [Updating dependencies](https://github.com/alphagov/notifications-manuals/wiki/Dependencies)
