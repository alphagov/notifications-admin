// general helpers, not related to the DOM and usable in different contexts

// turn a list of key=value pairs (like tuples) into data that can be sent via AJAX
// taken from https://developer.mozilla.org/en-US/docs/Learn/HTML/Forms/Sending_forms_through_JavaScript
// but requiring an array as input rather than a hash, to preserve order of pairs
function getFormDataFromPairs (pairs) {

  const urlEncodedDataPairs = [];

  pairs.forEach(pair => {

    urlEncodedDataPairs.push(`${window.encodeURIComponent(pair[0])}=${window.encodeURIComponent(pair[1])}`);

  });

  return urlEncodedDataPairs.join('&');

};

exports.getFormDataFromPairs = getFormDataFromPairs;
