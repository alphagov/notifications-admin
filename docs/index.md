About this document
==========================
This document is for developers, technical architects, and service managers who want to use the GOV.UK Notify platform to send notifications to users of their digital service. 

About GOV.UK Notify
====================
GOV.UK Notify is a cross-government platform, currently in beta, that lets government services and agencies [?] send notifications by sms or email. 

There are two ways to send notifications:

* use the GOV.UK Notify interface
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

  At first your service will be in trial mode. When you’re fully integrated and ready to go live, send a request to the GOV.UK Notify team. 

3. Add a template so you can send sms and email notifications. You can personalise the template using double brackets for replaceables. For example: 

  Dear ((name))

  Your ((item)) will expire on ((date)). 

4. Upload a csv file containing the list of recipients and replaceables. 
5. Send an sms or email notification.
6. Create a new API key. This will be used to connect to the API.

  You can provide all your developers with test keys so they can experiment in the Sandbox environment. But keep the number of keys for real integrations to a minimum number of people on your team. 




Integrate the GOV.UK API into your service
============================================

A client (on github) will make calls to GOV.UK Notify on your behalf. 

You can either:
* use a client library provided by Notify - there is currently 1 python library but more will be added in different languages
* develop your own [???]

To make an IPA call to a client you need:
* the service ID - this is aviailable under API keys on the GOV.UK Notify interface
* an API key - this is a secret key so save it somewhere safe; do not commit API keys to public source code repositories

API integration
------------------


API endpoints
----------------

You can use the API to:
* send notifications
* retrieve one or more notifications
* retrieve all notifications

To send a text notification: 
```
POST /notifications/sms
```

```
{
  'to': '+447700900404',
  'template': 1
}
```
where ‘to’ is the phone number and ‘template’ is the template ID to send.

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
To get the status of a single text notification:
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
where ‘status’ is the the status of the notification. 


To get the status of all text notifications: [do we want this? why do we only explain how to get text notifciations, do we want to explain how to do the same for email notifications?]




Functional testing
---------------------
[Some info in Rosalie’s notes.]
 

Security
----------
[Some info in Rosalie’s notes.]

Privacy
--------









