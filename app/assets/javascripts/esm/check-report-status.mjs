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
    // if (!isSupported()) {
    //   return this;
    // }

    this.$module = $module;
    this.fetchInterval = 20000;
    this.redirectDelay = 10000;
    this.reportStatusEndpoint = `${location.pathname}/status.json`;
    this.reportReadyStatus = 'stored';
    this.reportFailedStatus = 'failed';
    this.currentCheck = null;

  }

  runCheck() {
    this.currentCheck = this.checkStatus();
  }

  async checkStatus() {
    try {
      const response = await fetch(this.reportStatusEndpoint);
      if (!response.ok) {
        throw new Error('Error checking report status: no response');
      }
      const data = await response.json();
      this.processStatus(data.status);
    } catch (error) {
      console.error('Error checking report status:', error);
      setTimeout(this.runCheck.bind(this), this.fetchInterval);
    }
  }

  processStatus(status) {
    if (status === this.reportReadyStatus || status === this.reportFailedStatus) {
      this.updatePageText();
      setTimeout(() => {
        location.replace(location.pathname);
      }, this.redirectDelay);
    } else {
      setTimeout(this.runCheck.bind(this), this.fetchInterval);
    }
  }

  updatePageText() {
    const statusUpdateText = document.createElement('p');
    statusUpdateText.classList.add('govuk-body');
    statusUpdateText.textContent = 'Report status has been updated. We will redirect you shortly.';
    this.$module.innerHTML = '';
    this.$module.append(statusUpdateText);
  }
}

export default CheckReportStatus;
