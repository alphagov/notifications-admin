About this documentation
==========================
This documentation is for developers, technical architects, and service managers who want to use the GOV.UK Notify platform to send notifications to users of their digital service. 

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

3. From the dashboard, add templates to be able to send sms and email notifications. You can personalise the template using double brackets for replaceables. For example: 

  Dear ((name))

  Your ((item)) will expire on ((date)). 

4. Upload a csv file containing the list of recipients and replaceables. 
5. Send an sms or email notification.
6. Create a new API key. This will be used for ???.



Integrate the GOV.UK API into your service
============================================

API integration
------------------


API endpoints
----------------


Functional testing
---------------------
[Some info in Rosalie’s notes.]
 

Security
----------
[Some info in Rosalie’s notes.]

Privacy
--------









