import { isSupported } from 'govuk-frontend';

/*
This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
that uses ES2015 Classes -
https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton

It replaces the previously used way of setting methods on the component's `prototype`.
We use a class declaration way of defining classes -
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class

More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

This module is intended to be used to show and hide an error banner based on a javascript trigger. You should make
sure the banner has an appropriate aria-live attribute, and a tabindex of -1 so that screenreaders and keyboard users
are alerted to the change respectively.

This may behave in unexpected ways if you have more than one element with the `govuk-error-summary` class on your page.
*/
class ErrorBanner {
  constructor(selector) {
    if (!isSupported()) {
      return this;
    }
    /* 
    authenticate and register security keys have 3 error banners:
    no-js, no-webauth support and one for error in getting/setting creds
    old JS used to toggle display of all 3.

    now, we pass a selector that we want to toggle but still use
    govuk-error-summary as the default
    */
    selector = selector || '.govuk-error-summary';
    this.$bannerElement = document.querySelector(selector);
  }   

  hideBanner() {
    this.$bannerElement.setAttribute('hidden','hidden');
  }

  showBanner() {
    this.$bannerElement.removeAttribute('hidden');
    this.$bannerElement.focus();
  }
}

export default ErrorBanner;
