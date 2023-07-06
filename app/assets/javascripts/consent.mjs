function hasConsentFor (cookieCategory, consentCookie) {
  if (consentCookie === undefined) { consentCookie = window.GOVUK.getConsentCookie(); }

  if (consentCookie === null) { return false; }

  if (!(cookieCategory in consentCookie)) { return false; }

  return consentCookie[cookieCategory];
}

export { hasConsentFor };
