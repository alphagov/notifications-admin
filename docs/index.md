<h1> API documentation</h1>

This document is for central government developers and technical architects who want to use the GOV.UK Notify platform to send notifications to users of their digital service.

* [About GOV.UK Notify](#about_Notify)
* [Before you start](#beforestart)
* [Integrate the GOV.UK Notify API into your service](#integrate_Notify)
    * [Authenticate requests](#AuthRequests)
    * [JSON Web Tokens: claims](#JWT_claims)
    * [API client libraries](#client_libraries)
* [test_integ](#Testing your integration with GOV.UK Notify)
    * [API_keys](#API keys)
* [API endpoints](#API_endpoints)
    * [Send notifications: POST](#sendnotifications)
    * [Retrieve notifications: GET](#getnotifications)
    * [Authorisation error messages](#autherror_code)
    * [Other error messages](#othererror_code)
* [GOV.UK Notify API code](#Notify_code)



<h2 id="about_Notify">About GOV.UK Notify</h2>

GOV.UK Notify is a cross-government platform that lets government services send notifications by text or email. It's currently in beta.

There are 2 ways to send notifications:

* use the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application
* [integrate your web applications or back office systems](#integrate_Notify) with the GOV.UK Notify API

The GOV.UK Notify allows you to [send notifications (POST)](#sendnotifications) and [get the status of notifications (GET)](#getnotifications) you have sent.

To find out more about GOV.UK Notify, see the [Government as a Platform](https://governmentasaplatform.blog.gov.uk/) blog.

<h2 id="beforestart">Before you start</h2>

  1. Register for a [GOV.UK Notify](https://www.notifications.service.gov.uk/) account.

    You'll need an email address from a local or central government organisation and your mobile phone for 2-factor authentication.

  2. Add a template so you can send text and email notifications.

    **Note:** A template is required even if you send notifications with the GOV.UK Notify API.

    You can personalise the template using double brackets for placeholders. For example:

    > Dear ((name)),
    >
    > Your ((item)) is due for renewal on ((date)).

  3. Create an API key. This will be used to connect to the GOV.UK Notify API.

    Each service can have multiple API keys. This allows you to integrate several systems, each with its own key. You can also have separate keys for your development and test environments.

    **Important:** API keys are secret, so save them somewhere safe. Don't commit API keys to public source code repositories.

<h2 id="integrate_Notify">Integrate the GOV.UK Notify API into your service</h2>

There are 2 ways to integrate the API into your service:

* use one of the client libraries provided by GOV.UK Notify:
      
      * [Python library](https://github.com/alphagov/notifications-python-client/blob/master/README.md#usage)
      * [PHP library](https://github.com/alphagov/notifications-php-client/blob/master/README.md#usage)
      * [Java library](https://github.com/alphagov/notifications-java-client)

* develop your own integration to produce requests in the correct format

<h3 id="AuthRequests">Authenticate requests</h3>

GOV.UK Notify uses [JSON Web Tokens (JWT)](https://jwt.io/introduction/) for authentication and identification. The GOV.UK Notify client libraries encode and decode JSON Web Tokens when making requests to the GOV.UK Notify API.  If you don’t use one of these libraries, you must manually create tokens yourself.

For examples of how to encode and decode JSON Web Tokens, see [authentication.py](https://github.com/alphagov/notifications-python-client/blob/master/notifications_python_client/authentication.py) in the GOV.UK Notify Python client library, or the appropriate [PHP] (https://github.com/alphagov/notifications-php-client) or [Java] (https://github.com/alphagov/notifications-java-client) client library.

To create JSON Web Tokens you need:

* your Service ID – identifies your service
* your API key (in JSON Web Token terms this is called the client ID) – used to sign tokens during requests for API resources

To find your Service ID and create or revoke API keys, click on **API keys** in the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application.

<h3 id="JWT_claims">JSON Web Tokens: claims</h3>

JSON Web Tokens have a series of standard and application-specific claims.

JSON Web Token standard claims (these form the JSON Web Token header):
```
{
  "alg": "HS256",
  "typ": "JWT"
}
```

GOV.UK Notify application-specific claims (these form the JSON Web Token payload):
```
{
  iss: 'string', // Service ID
  iat: 0, // creation time in epoch seconds (UTC)
}
```

The header and payload are Base64Url encoded.

The verify signature is created using the HMAC SHA256 hashing algorithm.

<h3 id="client_libraries">API client libraries</h3>

GOV.UK Notify supports the following client libraries:

 * [GOV.UK Notify Python library](https://github.com/alphagov/notifications-python-client)
 * [GOV.UK Notify PHP library] (https://github.com/alphagov/notifications-php-client)
 * [GOV.UK Notify Java library] (https://github.com/alphagov/notifications-java-client)

These provide example code for calling the API and for creating API tokens.

<h2 id="test_integ">Testing your integration with GOV.UK Notify</h2>

Service teams should do all their testing within the GOV.UK Notify production environment (https://api.notifications.service.gov.uk).

You don’t need different service accounts or environments. Instead, there are 3 types of API key that let you do functional and performance integration testing.

<h3 id="API_keys">API keys</h3>

The types of API key that you can create within GOV.UK Notify are:

* normal key
* team key

<h4 id="normal_keys">Normal keys</h3>

Normal keys have the same permissions as the service:

* when the service is in ‘Trial mode’, you can only send to members of your team and you are restricted to 50 messages per day
* when the service is live, you can use the key to send messages to anyone

Messages sent with a normal key show up on your dashboard and count against your text message and email allowances.

There is no need to generate a new key when the service moves from trial to live.

Don’t use your normal key for automated testing.

<h4 id="team_keys">Team keys</h3>

Use a team key for end-to-end functional testing.

A team key lets you send real messages to members of your team. You get an error if you try to send messages to anyone else.

Messages sent with a team key show up on your dashboard and count against your text message and email allowances.


<h2 id="API_endpoints">API endpoints</h2>

You can use the GOV.UK Notify API to:

* send a [text](#sendtext) or [email](#sendemail) notification
* [retrieve the status of one notification](#get_single_notif)
* [retrieve the status of all notifications](#get_all_notif)

<h3 id="sendnotifications">Send notifications: POST</h3>

<a name="sendtext"></a>
To send a text notification:
```
POST /notifications/sms
```

```
{
  'to': '+447700900404',
  'template': f6895ff7-86e0-4d38-80ab-c9525856c3ff,
  'personalisation': {
    'name': 'myname',
    'date': '2016'
  }
}
```
See [below](#fieldsforPOST) for explanations of the fields.

<a name="sendemail"></a>
To send an email notification:
```
POST /notifications/email
```

```
{
  'to': 'email@gov.uk',
  'template': f6895ff7-86e0-4d38-80ab-c9525856c3ff,
    'personalisation': {
    'name': 'myname',
    'date': '2016'
  }
}
```
<a name="fieldsforPOST"></a>
where:

* `to` is a required string that indicates the recipient's phone number or email address
* `template` is a required string that indicates the Template ID to use

    **Note:** To access the Template ID from the [GOV.UK Notify](https://www.notifications.service.gov.uk/) web application, go to **Text message templates** or **Email templates** and click on **API info**.

* `personalisation` is an optional array that specifies the placeholders and values in your templates

    **Note:** You must provide all placeholders set up in your template. See [how to create placeholders in a template](#beforestart).

<a id="coderesponse"></a>
The response (status code 201) will be:
```
{
  'data':{
    'notification': {
      'id':1
    }
  }
}
```

where `id` is the unique identifier for the notification – you'll use this ID to retrieve the status of a notification.

<h3 id="getnotifications">Retrieve notifications: GET</h3>

<a name="get_single_notif"></a>
To retrieve the status of a single text or email notification:
```
GET /notifications/{id}
```
The response (status code 200) will be:

```
{
  'notification': {
    'status': 'delivered',
    'to': '07515 987 456',
    'template': {
      'id': '5e427b42-4e98-46f3-a047-32c4a87d26bb',
      'name': 'First template',
      'template_type': 'sms'
    },
    'created_at': '2016-04-26T15:29:36.891512+00:00',
    'updated_at': '2016-04-26T15:29:38.724808+00:00',
    'sent_at': '2016-04-26T15:29:37.230976+00:00',
    'job': {
      'id': 'f9043884-acac-46db-b2ea-f08cd8ec6d67',
      'original_file_name': 'Test run'
    },
    'sent_at': '2016-04-26T15:29:37.230976+00:00',
    'id': 'f163deaf-2d3f-4ec6-98fc-f23fa511518f',
    'content_char_count': 490,
    'service': '5cf87313-fddd-4482-a2ea-48e37320efd1',
    'reference': None,
    'sent_by': 'mmg'
  }
}
```
See [below](#fieldsforGET) for explanations of the fields.

<a name="get_all_notif"></a>
To retrieve the status of all notifications:
```
GET /notifications
```

The response (status code 200) will be:

```
{'notifications':
  [{
    'status': 'delivered',
    'to': '07515 987 456',
    'template': {
      'id': '5e427b42-4e98-46f3-a047-32c4a87d26bb',
      'name': 'First template',
      'template_type': 'sms'
    },
    'job': {
      'id': '5cc9d7ae-ceb7-4565-8345-4931d71f8c2e',
      'original_file_name': 'Test run'
    },
    'created_at': '2016-04-26T15:30:49.968969+00:00',
    'updated_at': '2016-04-26T15:30:50.853844+00:00',
    'sent_at': '2016-04-26T15:30:50.383634+00:00',
    'id': '04ae9bdc-92aa-4d6c-a0da-48587c03d4c7',
    'content_char_count': 446,
    'service': '5cf87313-fddd-4482-a2ea-48e37320efd1',
    'reference': None,
    'sent_by': 'mmg'
    },
    {
    'status': 'delivered',
    'to': '07515 987 456',
    'template': {
      'id': '5e427b42-4e98-46f3-a047-32c4a87d26bb',
      'name': 'First template',
      'template_type': 'sms'
    },
    'job': {
      'id': 'f9043884-acac-46db-b2ea-f08cd8ec6d67',
      'original_file_name': 'Test run'
    },
    'created_at': '2016-04-26T15:29:36.891512+00:00',
    'updated_at': '2016-04-26T15:29:38.724808+00:00',
    'sent_at': '2016-04-26T15:29:37.230976+00:00',
    'id': 'f163deaf-2d3f-4ec6-98fc-f23fa511518f',
    'content_char_count': 490,
    'service': '5cf87313-fddd-4482-a2ea-48e37320efd1',
    'reference': None,
    'sent_by': 'mmg'
    },
    …
  ],
  'links': {
    'last': '/notifications?page=3&template_type=sms&status=delivered',
    'next': '/notifications?page=2&template_type=sms&status=delivered'
  },
  'total': 162,
  'page_size': 50
}
```
<a name="fieldsforGET"></a>
where:

* `status` is the status of the notification; this can be `sending`, `delivered`, or `failed`
* `to` is the recipient's phone number or email address
* `template`:
    * `id` is the Template ID
    * `name` is the name of the template used
    * `template_type` is `sms` or `email`
* `created_at` is the full timestamp, in Coordinated Universal Time (UTC), at which GOV.UK Notify created the notification
* `updated_at` is the full timestamp, in Coordinated Universal Time (UTC), at which the notification was updated
* `sent_at` is the full timestamp, in Coordinated Universal Time (UTC), at which GOV.UK Notify sent the notification
* `job` is empty if you are using the API to send notifications:
    * `id` is the job ID
    * `original_file_name` is the name of the CSV file, if used
* `id` is the unique identifier for the process of sending and retrieving one or more notifications
* `content_char_count` indicates the full character count of the text notification, including placeholders (populated for text notifications only)
* `service` is your Service ID
* `reference` is used in the Notifications API so you can ignore it (populated for email notifications only)
* `sent_by` is the name of the provider
* `links`:
    * `last` is the URL of the last page of notifications
    * `next` is the URL of the next page of notifications
* `total` is the total number of notifications sent by the service using the given template type
* `page_size` is an optional integer indicating the number of notifications per page; if not provided, defaults to 50

The ``GET /notifications`` request accepts the following query string parameters:
  * `template_type` - `sms` or `email` (you can enter `template_type` twice)
  * `status` - `sending`, `delivered`, or `failed`
  * `page` - page number
  * `page_size` - number of notifications per page; defaults to 50
  * `limit_days` - number of days; defaults to 7


For example, to scroll through the pages in the list, run:

```
GET /notifications?page=2
```


<h3 id="autherror_code">Authorisation error messages</h3>


Error code | Body | Meaning
--- | --- | ---
401 | {"result": "error", <br> "message": "Unauthorized, authentication token must be provided"} | Authorisation header is missing from request
401 | {"result": "error", <br> "message": "Unauthorized, authentication bearer scheme must be used"} | Authorisation header is missing bearer
403 | {"result": "error", <br> "message": "Invalid token: signature"} | Unable to decode the JSON Web Token signature, due to missing claims
403 | {"result": "error", <br> "message": "Invalid credentials"} | Service ID in the `iss` claim is incorrect, or no valid API key for Service ID
403 | {"result": "error", <br> "message": "Invalid token: expired"} | Token is expired; there is a 30 second time limit



<h3 id="othererror_code">Other error messages</h3>

Error code | Body | Meaning
--- | --- | ---
429 | {"result": "error", <br> "message": "Exceeded send limits (50) for today"} | You have reached the maximum number of messages you can send per day
400 | {"result": "error", <br> "message": "id: required field"} | Post body is badly formed: missing `id` field
400 | {"result":"error", <br> "message":{'template': ['Missing personalisation: {template_placeholder_name}']} | Post body is badly formed: missing personalisation data
400 | {"result":"error", <br> "message"={'to': ['Invalid {notification_type} for restricted service')]} | Service is in trial mode; you cannot send messages to email addresses or phone numbers not belonging to team members

<h2 id="Notify_code">GOV.UK Notify API code</h2>

The GOV.UK Notify API code is open sourced at:

[GOV.UK Notify API](https://github.com/alphagov/notifications-api)
