(function (window) {
  "use strict";

  var gaCookies = ['_ga', '_gid'];
  var notifyCookiePolicyCookie = 'cookies_policy';

  for (var i = 0; i < gaCookies.length; i++) {
    if (getCookie(gaCookies[i])) {
      // GA cookies are set on the base domain so need the www stripping
      document.cookie = gaCookies[i] + '=;expires=' + new Date(0).toGMTString() + ';domain=' + window.location.hostname.replace(/^www\./, '.') + ';path=/';
    }
  }

  if (getCookie(notifyCookiePolicyCookie)) {
    document.cookie = notifyCookiePolicyCookie + '=;expires=' + new Date(0).toGMTString() + ';path=/';
  }

function getCookie(name) {
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
}

})(window);