# Setup

Create a personal access token: https://github.com/settings/personal-access-tokens/new

Give it access to only selected repositories, then select the following repositories:

* notifications-api
* notifications-admin
* notifications-template-preview
* notifications-antivirus
* document-download-api
* document-download-frontend

Give it read-write access to 'contents' and 'pull requests'

---

Configure codespace secrets here: https://github.com/settings/codespaces

Add a secret `GH_TOKEN` with the personal access token you generated previously. Make it available to the `notifications-admin` repository.

Ask a developer for an AWS access key pair and insert new codespace secrets called `GH_AWS_ACCESS_KEY_ID` and `GH_AWS_SECRET_ACCESS_KEY`. Make them both available to the `notifications-admin` repository.

# Running

Launch a codespace via GitHub:

* (work-in-progress): switch to the 'SW-codespace' branch on `notifications-admin` project.
* Click the green 'Code' button, switch to the 'Codespaces' tab, and press the 'three dots menu'. Select 'New with options...'
* Change the machine type from '2 core' to '4 core', then click 'Create codespace'.
* Wait for the browser tab to load and a terminal to appear at the bottom. After a few seconds the display should show a command running. Wait for 'postCreateCommand' to report as complete.
* Type './start-notify-in-codespace.sh' into the terminal, enter your email address and password at the prompt, and then wait for Notify to build and launch.
* Once Notify has started running (takes ~15 minutes the first time), click the 'Ports' tab, hover over the 'Local address' row, and click the 'globe'/'www' icon to launch a new browser window with Notify.

# Issues

* Fonts are not loading correctly.
* A number of 'full' Notify features may not work, such as template previews, sending text messages, document download, etc.
  * In part this is due to the network/hostname configuration. Services running inside docker need to talk on their development port, but when URLs are exposed externally GitHub only makes them available on port 80.
