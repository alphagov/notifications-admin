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
    this.$component = $module;

    this.checkStatus();

  }

  checkStatus() {
    const fetchInterval = 20000; // 20s
    const reportStatusEndpoint = `${location.pathname}/status.json`;
    const reportReadyStatus = 'completed';

    const request = async () => {
      try {
          const response = await fetch(reportStatusEndpoint);
          const data = await response.json();

          if (data.status === reportReadyStatus) {
            // run update text
            this.updatePageText()
            // run redirect
            return;
          }

          setTimeout(request, fetchInterval);

      } catch (error) {
        console.error('Error checking status', error);
      }
    };
    request();
  }

  updatePageText() {
    document.body.innerHTML = 'yes'
  }
}

export default CheckReportStatus;
