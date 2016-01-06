[![Build Status](https://api.travis-ci.org/alphagov/notifications-admin.svg?branch=master)](https://api.travis-ci.org/alphagov/notifications-admin.svg?branch=master)


# notifications-admin
Application to handle the admin functions of the notifications application.

### Features of this application:
<ul>
 <li>Register users
 <li>Register services
 <li>Download CSV for an email or sms batch
 <li>Show history of notifications
 <li>Reports
</ul>

### Create a virtual environment for this project
```shell
    mkvirtualenv -p /usr/local/bin/python3 notifications-admin
```


### Building the frontend

You need [Node](http://nodejs.org/) which will also get you [NPM](npmjs.org),
Node's package management tool.
```shell
    brew install node
```

n is a tool for managing different versions of node. The following installs n and uses the latest version of node.

    npm install -g n
    n latest
    npm rebuild node-sass
 
Most of the frontend dependencies are managed using Git Submodules. Some are
managed with NPM and Bower. To install or update *all the things*, run
```shell
    git submodule init 
    git submodule update
    npm install
```

If you want the front end assets to re-compile on changes, leave this running
in a separate terminal from the app
```shell
    npm run watch
```

### Running the application:
```shell
    pip install -r requirements.txt
    ./scripts/bootstrap.sh  
    ./scripts/run_app.sh
```

Note: the ./scripts/bootstrap.sh script only needs to be run the first time to
create the database.

URL to test app:

    localhost:6012/helloworld


### Domain model

All the domain models are defined in the
[models.py](https://github.com/alphagov/notifications-admin/blob/master/app/models.py)
file.
