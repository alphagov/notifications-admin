### What is it?

This is a simple static error page to present to users in case of a (planned) downtime.
It is deployed as an individual app and remains dormant until a route is assigned to it.


### How do I use it?

It should already be deployed, but if not you can deploy it by running

    cf push notify-admin-failwhale

To direct traffic to it you need to update the routes by running

    cf map-route notify-admin-failwhale [ENVIRONMENT-URL] --hostname www
    cf unmap-route notify-admin [ENVIRONMENT-URL] --hostname www

To remove admin failwhale:

    cf map-route notify-admin [ENVIRONMENT-URL] --hostname www
    cf unmap-route notify-admin-failwhale [ENVIRONMENT-URL] --hostname www


Where [ENVIRONMENT-URL] would be one of:

- notify.works for preview
- notify-staging.works for staging
- notifications.service.gov.uk for production

**Make sure you are on the correct environment!**
