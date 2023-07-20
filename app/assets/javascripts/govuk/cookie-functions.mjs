var DEFAULT_COOKIE_CONSENT = {
  'analytics': false
};

var COOKIE_CATEGORIES = {
  '_ga': 'analytics',
  '_gid': 'analytics'
};

/*
  Cookie methods
  ==============

  Usage:

    Setting a cookie:
    cookie('hobnob', 'tasty', { days: 30 });

    Reading a cookie:
    cookie('hobnob');

    Deleting a cookie:
    cookie('hobnob', null);
*/
var cookie = function (name, value, options) {
  if (typeof value !== 'undefined') {
    if (value === false || value === null) {
      return setCookie(name, '', { days: -1 });
    } else {
      // Default expiry date of 30 days
      if (typeof options === 'undefined') {
        options = { days: 30 };
      }
      return setCookie(name, value, options);
    }
  } else {
    return getCookie(name);
  }
};

var getConsentCookie = function () {
  var consentCookie = cookie('cookies_policy');
  var consentCookieObj;

  if (consentCookie) {
    try {
      consentCookieObj = JSON.parse(consentCookie);
    } catch (err) {
      return null;
    }

    if (typeof consentCookieObj !== 'object' && consentCookieObj !== null) {
      consentCookieObj = JSON.parse(consentCookieObj);
    }
  } else {
    return null;
  }

  return consentCookieObj;
};

var setConsentCookie = function (options) {
  var cookieConsent = getConsentCookie();

  if (!cookieConsent) {
    cookieConsent = JSON.parse(JSON.stringify(DEFAULT_COOKIE_CONSENT));
  }

  for (var cookieType in options) {
    cookieConsent[cookieType] = options[cookieType];

    // Delete cookies of that type if consent being set to false
    if (!options[cookieType]) {
      for (var cookie in COOKIE_CATEGORIES) {
        if (COOKIE_CATEGORIES[cookie] === cookieType) {
          cookie(cookie, null);

          if (cookie(cookie)) {
            document.cookie = cookie + '=;expires=' + new Date() + ';domain=' + window.location.hostname.replace(/^www\./, '.') + ';path=/';
          }
        }
      }
    }
  }

  setCookie('cookies_policy', JSON.stringify(cookieConsent), { days: 365 });
};

var checkConsentCookieCategory = function (cookieName, cookieCategory) {
  var currentConsentCookie = getConsentCookie();

  // If the consent cookie doesn't exist, but the cookie is in our known list, return true
  if (!currentConsentCookie && COOKIE_CATEGORIES[cookieName]) {
    return true;
  }

  currentConsentCookie = getConsentCookie();

  // Sometimes currentConsentCookie is malformed in some of the tests, so we need to handle these
  try {
    return currentConsentCookie[cookieCategory];
  } catch (e) {
    console.error(e);
    return false;
  }
};

var checkConsentCookie = function (cookieName, cookieValue) {
  // If we're setting the consent cookie OR deleting a cookie, allow by default
  if (cookieName === 'cookies_policy' || (cookieValue === null || cookieValue === false)) {
    return true;
  }

  if (COOKIE_CATEGORIES[cookieName]) {
    var cookieCategory = COOKIE_CATEGORIES[cookieName];

    return checkConsentCookieCategory(cookieName, cookieCategory);
  } else {
    // Deny the cookie if it is not known to us
    return false;
  }
};

var setCookie = function (name, value, options) {
  if (checkConsentCookie(name, value)) {
    if (typeof options === 'undefined') {
      options = {};
    }
    var cookieString = name + '=' + value + '; path=/; SameSite=Lax';
    if (options.days) {
      var date = new Date();
      date.setTime(date.getTime() + (options.days * 24 * 60 * 60 * 1000));
      cookieString = cookieString + '; expires=' + date.toGMTString();
    }
    if (document.location.protocol === 'https:') {
      cookieString = cookieString + '; Secure';
    }
    document.cookie = cookieString;
  }
};

var getCookie = function (name) {
  var nameEQ = name + '=';
  var cookies = document.cookie.split(';');
  for (var i = 0, len = cookies.length; i < len; i++) {
    var cookie = cookies[i];
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1, cookie.length);
    }
    if (cookie.indexOf(nameEQ) === 0) {
      return decodeURIComponent(cookie.substring(nameEQ.length));
    }
  }
  return null;
};

export {
  cookie,
  getConsentCookie,
  setConsentCookie,
  checkConsentCookieCategory,
  checkConsentCookie,
  getCookie,
  setCookie
}
