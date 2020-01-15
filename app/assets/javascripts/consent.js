(function (window) {
  "use strict";

  function hasConsentFor (cookieCategory) {
    const consentCookie = window.GOVUK.getConsentCookie();

    if (consentCookie === null) { return false; }

    if (!(cookieCategory in consentCookie)) { return false; }

    return consentCookie[cookieCategory];
  }

  window.GOVUK.hasConsentFor = hasConsentFor;
})(window);
