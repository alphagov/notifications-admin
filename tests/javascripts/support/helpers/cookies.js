// Helper for deleting a cookie
function deleteCookie (cookieName) {

  document.cookie = cookieName + '=; path=/; expires=' + (new Date());

};

function setCookie (name, value, options) {
  if (typeof options === 'undefined') {
    options = {};
  }
  var cookieString = name + '=' + value + '; path=/;domain=' + window.location.hostname;
  if (options.days) {
    var date = new Date();
    date.setTime(date.getTime() + (options.days * 24 * 60 * 60 * 1000));
    cookieString = cookieString + '; expires=' + date.toGMTString();
  }
  document.cookie = cookieString;
};

exports.deleteCookie = deleteCookie;
exports.setCookie = setCookie;
