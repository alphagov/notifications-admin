# notifications-admin

GOV.UK Notify admin application - https://www.notifications.service.gov.uk/

 - Register and manage users
 - Create and manage services
 - Send batch emails and SMS by uploading a CSV
 - Show history of notifications

## Setting up

### Python version

At the moment we run Python 3.6 in production.

### NPM packages

```shell
brew install node
```

[NPM](npmjs.org) is Node's package management tool. `n` is a tool for managing different versions of Node. The following installs `n` and uses the long term support (LTS) version of Node.

```shell
npm install -g n
n lts
```

### `environment.sh`

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

## To run the application

```shell
# install dependencies, etc.
make bootstrap

# run the web app
make run-flask
```

Then visit [localhost:6012](http://localhost:6012).

## To test the application

```
# install dependencies, etc.
make bootstrap

make test
```

## Common tasks

### Updating application dependencies

`requirements.txt` is generated from the `requirements.in` in order to pin versions of all nested dependencies. If `requirements.in` has been changed, run `make freeze-requirements` to regenerate it.

### Automatically rebuild the frontend assets

If you want the front end assets to re-compile on changes, leave this running in a separate terminal from the app

```shell
    npm run watch
```

## Further docs

- [Working with static assets](docs/static-assets.md)
