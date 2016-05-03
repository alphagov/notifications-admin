# API documenation

<a name="about_doc"></a>
## About this document

This document is for central government developers, technical architects, and service managers who want to use the GOV.UK Notify platform to send notifications to users of their digital service.

<a name="about_Notify"></a>
## About GOV.UK Notify

GOV.UK Notify is a cross-government platform that lets government services send notifications by sms or email. It is currently in beta.

There are 2 ways to send notifications:

* use the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application
* [integrate your web applications or back office systems](#integrate_Notify) with the GOV.UK Notify API

To find out more about GOV.UK Notify, see the [Government as a Platform](https://governmentasaplatform.blog.gov.uk/) blog.

<a name="before_start"></a>
## Before you start

To use GOV.UK Notify, you need:

* an email address from a local or central government organisation
* a mobile number for 2-factor authentication

<a name="quickstart"></a>
## Quick start guide to GOV.UK Notify

To get started:

  1. Register for a [GOV.UK Notify](https://www.notifications.service.gov.uk/) account. You will need your mobile phone for 2-factor authentication.

  2. Add a new service.

    At first your service will be in trial mode. In trial mode, you can send up to 50 test notifications per day to yourself and your team members. When you’re fully integrated and ready to go live, send a request to the GOV.UK Notify team.

  3. Add a template so you can send sms and email notifications. 

    **Note:** A template is required even if you send notifications with the GOV.UK Notify API.
 
    You can personalise the template using double brackets for placeholders. For example:

    > Dear ((name)),
    >
    > Your ((item)) is due for renewal on ((date)).

  4. You can upload a csv file containing a header row matching the placeholders in your template, and data rows with values to use for the placeholders.

  5. Send an sms or email notification.

  6. If you intend to use the GOV.UK Notify API, create a new API key. This will be used to connect to the GOV.UK Notify API.

    Each service can have multiple API keys. This allows you to integrate several systems, each with its own key. You can also have separate keys for your development and test environments.
    
    **Important:** API keys are secret, so save them somewhere safe. Do not commit API keys to public source code repositories. 

<a name="integrate_Notify"></a>
## Integrate the GOV.UK Notify API into your service

GOV.UK Notify provides an API that allows you to create text and email notifications and get the status of notifications you have sent.

<a name="API_integration"></a>
### API integration

![Notfy](/static/images/notify-diagram.png)

There are 2 ways to integrate the API into your service:

* use one of the client libraries provided by GOV.UK Notify:
    * [Python library](https://github.com/alphagov/notifications-python-client)
    * [PHP library] (https://github.com/alphagov/notifications-php-client) 
    * [Java library] (https://github.com/alphagov/notifications-java-client) 
* develop your own integration to produce requests in the correct format

GOV.UK Notify uses [JSON Web Tokens (JWT)](https://jwt.io/) for authentication and identification. The GOV.UK Notify client libraries encode and decode JSON Web Tokens when making requests to the GOV.UK Notify API.  If you don’t use one of these libraries, you must manually create tokens yourself. 

For examples of how to encode and decode JSON Web Tokens, see [authentication.py](https://github.com/alphagov/notifications-python-client/blob/master/notifications_python_client/authentication.py) in the GOV.UK Notify Python client library, or the appropriate [PHP] (https://github.com/alphagov/notifications-php-client) or [Java] (https://github.com/alphagov/notifications-java-client) client library.

A JSON Web Token contains, in encrypted format:

* your service ID – identifies your service
* your API key (in JSON Web Token terms this is called the client ID) – used to sign tokens during requests for API resources

Use the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application to find your service ID and create API keys. 

<a name="JWT_claims"></a>
### JSON Web Tokens: claims

JSON Web Tokens have a series of standard and application-specific claims.

JSON Web Token standard claims:
```
{
  "alg": "HS256",
  "typ": "JWT"
}
```

GOV.UK Notify application-specific claims:
```
{
  iss: 'string', // service id
  iat: 0, // creation time in  epoch seconds (UTC)
}
```

The signing algorithm is the HMAC signature, using the provided key SHA256 hashing algorithm.

<a name="client_libraries"></a>
### API client libraries

GOV.UK Notify supports the following client libraries:

 * [GOV.UK Notify Python library](https://github.com/alphagov/notifications-python-client) 
 * [GOV.UK Notify PHP library] (https://github.com/alphagov/notifications-php-client)
 * [GOV.UK Notify Java library] (https://github.com/alphagov/notifications-java-client)

These provide example code for calling the API and for constructing the API tokens.

<a name="API_endpoints"></a>
### API endpoints

You can use the GOV.UK Notify API to:

* send an [sms](#sendsms) or [email](#sendemail) notification 
* [retrieve the status of one notification](#get_single_notif) 
* [retrieve the status of all notifications](#get_all_notif)  

<a name="sendsms"></a>
To send an sms notification:
```
POST /notifications/sms
```

```
{
  'to': '+447700900404',
  'template': 1, 
  'personalisation': {
    'name': 'myname',
    'date': '2016'
  }
}
```
<a name="sendemail"></a>
To send an email notification:
```
POST /notifications/email
```

```
{
  'to': 'email@gov.uk',
  'template': 1,
    'personalisation': {
    'name': 'myname',
    'date': '2016'
  }
}
```

where:

* `to` is the phone number or email address (required)
* `template` is the template ID to send (required)
   
    **Note:** To access the template ID from the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application, go to **Text message templates** or **Email templates** and click on **API info**.

* `personalisation` (optional) specifies the values for the placeholders in your templates

    **Note:** You must provide all placeholders set up in your template. See [how to create placeholders in a template](#quickstart).

<a id="coderesponse"></a>
The response will be:
```
{
   'data':{
      'notification': {
         'id':1
      }
   }
}
```

where `id` is the unique identifier for the notification – you will use this id to retrieve the status of a notification.

<a name="get_single_notif"></a>
To retrieve the status of a single sms or email notification:
```
GET /notifications/{id}
```

```
{
   'data':{
      'notification': {
         'status':'delivered',
         'created_at':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'template_type':'sms',
         'sent_at':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'job_id':1,
         'sender':'sms-partner'
      }
   }
}
```
where:

* `status` is the the status of the notification; this can be `sending`, `delivered`, or `failed` 
* `to` is the phone number or email address
* `template_type` is `sms` or `email`
* `sent_at` is the full timestamp, in Coordinated Universal Time (UTC), at which the notification was sent
* `message` is the content of message
* `job_id` is the unique identifier for the process of sending and retreiving one or more notifications
* `sender` may be the provider

The above fields are populated once the message has been processed; initially you get back the [response](#coderesponse) indicated above.

<a name="get_all_notif"></a>
To retrieve the status of all notifications: 
```
GET /notifications
```

```
{
   'data':[{
      'notification': {
         'status':'delivered',
         'created_at':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'template_type':'sms',
         'sent_at':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'job_id':1,
         'sender':'sms-partner'
      }
   },
   {
         'notification': {
         'status':'delivered',
         'created_at':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'template_type':'email',
         'sent_at':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'job_id':1,
         'sender':'email-partner'
      }
   }…]
}
```
This list is split into pages. To scroll through the pages run:

```
GET /notifications?&page=2
```

<a name="Notify_code"></a>
### GOV.UK Notify API code

The GOV.UK Notify API code is open sourced at:

[GOV.UK Notify API](https://github.com/alphagov/notifications-api) 






