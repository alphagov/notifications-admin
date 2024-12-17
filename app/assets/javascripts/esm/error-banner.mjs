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

class ErrorBanner {
   /*
  This module is intended to be used to show and hide an error banner based on a javascript trigger. You should make
  sure the banner has an appropriate aria-live attribute, and a tabindex of -1 so that screenreaders and keyboard users
  are alerted to the change respectively.

  This may behave in unexpected ways if you have more than one element with the `govuk-error-summary` class on your page.
  */
  constructor() {
    if (!isSupported()) {
      return this;
    }
    // yes some pages have more than one error summary on the page
    // depending on if there's no JS or no webuth support
    this.errorSummaryArray = document.querySelectorAll('.govuk-error-summary');
  }
  hideBanner() {
    this.errorSummaryArray.forEach(errorSummary => {
      errorSummary.classList.add('govuk-!-display-none');
    });
  }
  showBanner() {
    this.errorSummaryArray.forEach(errorSummary => {
      errorSummary.classList.remove('govuk-!-display-none');
      // is works as before but it feels strange to apply focus to all
      errorSummary.focus();
    });
  }
}

export default ErrorBanner;
