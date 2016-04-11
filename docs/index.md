About this document
==========================
This document is for developers, technical architects, and service managers who want to use the GOV.UK Notify platform to send notifications to users of their digital service.

About GOV.UK Notify
====================
GOV.UK Notify is a cross-government platform, currently in beta, that lets government services and agencies [?] send notifications by sms or email.

There are two ways to send notifications:

* use the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application
* integrate your web applications or back office systems with the GOV.UK Notify API

To find out more about GOV.UK Notify, see the [Government as a Platform](https://governmentasaplatform.blog.gov.uk/) blog.

Before you start
==================

To use GOV.UK Notify, you need:

* an email address from a local or central government organisation
* a mobile number for 2-factor authentication


Quick start guide to GOV.UK Notify
===================================

To get started:

1. Register for a [GOV.UK Notify](https://www.notifications.service.gov.uk/) account. You will need your mobile phone for 2-factor authentication.
2. Add a new service.

  At first your service will be in trial mode. In trial mode you will only be able to send test sms and email notifications to your own mobile number or email address. When you’re fully integrated and ready to go live, send a request to the GOV.UK Notify team.

3. Add a template so you can send sms and email notifications. You can personalise the template using double brackets for replaceables. For example:

  Dear ((name))

  Your ((item)) will expire on ((date)).

4. Upload a csv file containing a header row with the replaceables in your template, and data rows with values for the replaceables.
5. Send an sms or email notification.
6. Create a new API key. This will be used to connect to the API.

  You can provide all your developers with test keys so they can experiment in the Sandbox environment. But keep the number of keys for real integrations to a minimum number of people on your team.


Integrate the GOV.UK API into your service
============================================

GOV.UK.Notify provides an API that allows you to create text and email[?] notifications and get the status of notifications you have sent.

![Notfy](Notify.png)

There are two ways to integrate the API into your service:
* use a client library provided by Notify - there is currently 1 python library but more will be added in different languages
* develop your own client [?]

GOV.UK.Notify uses [JWT tokens](https://jwt.io/) for authentication and identification. JWT tokens are built into our pre-built clients. [you just have to do get service, it returns id]
If you don't use a pre-built client you must manually create the token which uses the service ID and API key [is it the token that uses the service ID and API key]?

To create a JWT token you need:
* the service ID (in JWT token terms this is called the client ID) - identifies your service; you can find the service ID under API keys on the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application 
* an API key - used to create an individual request for an API resource;  create this in the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application; it is a secret key so save it somewhere safe - do not commit API keys to public source code repositories

A client (on github) will make calls to GOV.UK Notify on your behalf.

The token takes the payload, serializes the JSON, shares the secret (service ID), and then puts them in order and encrypts. [from Rosalie's notes]



essentially it creates urls
 if using a language that we don't have a library for you have to de


API integration
------------------


API endpoints
----------------

You can use the API to:
* send a notification
* retrieve one notification
* retrieve all notifications

To send a text notification:
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
where:
* ‘to’ is the phone number (required)
* ‘template’ is the template ID to send (required)
* personalisation (optional) specifies the replaceables [where do these come from, the csv file?]


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

To retrieve the status of a single text or email notification:
```
GET /notifications/{id}
```

```
{
   'data':{
      'notification': {
         'status':'sent',
         'createdAt':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'method':'sms',
         'sentAt':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'jobId':1,
         'sender':'sms-partner'
      }
   }
}
```
where 
* ‘status’ is the the status of the notification.
* 'status' can be 'sent', 'delivered',  'failed', 'complaint', 'bounce'
* 'method' is sms or email
* 'jobId' is unique identifier for the process of sending the notification.
* 'message' - contents of message
* 'sender' - ??? may be provider???

The above fields are populated once the message has been processed, initially you just get back the response above)
CATH - send email with status responses

To get the status of all notifications: 
```
GET /notifications
```

```
{
   'data':[{
      'notification': {
         'status':'sent',
         'createdAt':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'method':'sms',
         'sentAt':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'jobId':1,
         'sender':'sms-partner'
      }
   },
   {
         'notification': {
         'status':'sent',
         'createdAt':'2016-01-01T09:00:00.999999Z',
         'to':'+447827992607',
         'method':'email',
         'sentAt':'2016-01-01T09:01:00.999999Z',
         'id':1,
         'message':'...',
         'jobId':1,
         'sender':'email-partner'
      }
   }...]
}
```
This list will be split into pages. To scroll through the pages run:

```
GET /notifications?&page=2
```





Functional testing
---------------------
[Some info in Rosalie’s notes.]


Security
----------
[Some info in Rosalie’s notes.]

Privacy
--------









