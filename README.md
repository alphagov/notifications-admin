https://travis-ci.org/alphagov/notifications-admin.svg

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
  mkvirtualenv -p /usr/local/bin/python3 notifications-admin

### GOV.UK frontend toolkit
 The GOV.UK frontend toolkit is a submodule of this project.
 To get the content of the toolkit run the following two commands

  git submodule init
  git submodule update


### To run the sample application run:
   pip install -r requirements.txt
   python app.py
