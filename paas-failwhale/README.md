### What is it?

This is a simple static error page to present to users in case of a (planned) downtime.
It is deployed as an individual app and remains dormant until a route is assigned to it.


### How do I use it?

It should already be deployed, but if not you can deploy it by running

    cf push notify-admin-failwhale

To enable it you need to run

    make <environment> enable-failwhale

and to disable it

    make <environment> disable-failwhale


Where `<environment>` is any of

- preview
- staging
- production
