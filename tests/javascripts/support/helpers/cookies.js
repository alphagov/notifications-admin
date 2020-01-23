// Helper for deleting a cookie
function deleteCookie (cookieName, options) {
  if (typeof options === 'undefined') {
    options = {};
  }
  if (!options.domain) { options.domain = window.location.hostname; }
  document.cookie = cookieName + '=; path=/; domain=' + options.domain + '; expires=' + (new Date());
};

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

exports.deleteCookie = deleteCookie;
exports.setCookie = setCookie;
