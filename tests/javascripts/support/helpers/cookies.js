function setCookie (name, value, options) {
  if (typeof options === 'undefined') {
    options = {};
  }
  if (!options.domain) { options.domain = window.location.hostname; }
  var cookieString = name + '=' + value + '; path=/; domain=' + options.domain;
  if (options.days) {
    var date = new Date();
    date.setTime(date.getTime() + (options.days * 24 * 60 * 60 * 1000));
    cookieString = cookieString + '; expires=' + date.toGMTString();
  }
  document.cookie = cookieString;
};

function getCookie(name) {
  var nameEQ = name + '=';
  var cookies = document.cookie.split(';')
  for (var i = 0, len = cookies.length; i < len; i++) {
    var cookie = cookies[i]
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1, cookie.length)
    }
    if (cookie.indexOf(nameEQ) === 0) {
      return decodeURIComponent(cookie.substring(nameEQ.length))
    }
  }
  return null
}

exports.setCookie = setCookie;
exports.getCookie = getCookie;
