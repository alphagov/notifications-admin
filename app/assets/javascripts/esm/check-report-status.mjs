import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class CheckReportStatus {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.$module = $module;

    this.checkStatus();

  }

  checkStatus() {
    const fetchInterval = 20000; // 20s
    const reportStatusEndpoint = `${location.pathname}/status.json`;
    const reportReadyStatus = 'stored';
    const reportFailedStatus = 'failed';

    const request = async () => {
      try {
          const response = await fetch(reportStatusEndpoint);
          const data = await response.json();

          if (data.status === reportReadyStatus || data.status === reportFailedStatus) {
            // inform user about the updated status
            this.updatePageTextAndRedirect();
            // redirect after 10s
            setTimeout( () => {
              location.replace(location.pathname);
           },10000);
           
            return;
          }
        // if no change to the status, keep checking
         setTimeout( () => { request() }, fetchInterval);

      } catch (error) {
        console.error('Error checking status', error);
      }
    };
    request();
  }

  updatePageTextAndRedirect() {
    const statusUpdateText = document.createElement('p');
    statusUpdateText.classList.add('govuk-body');
    statusUpdateText.textContent = 'Report status has been updated. We will redirect you shortly.'
    this.$module.innerHTML = '';
    this.$module.append(statusUpdateText);
  }
}

export default CheckReportStatus;
