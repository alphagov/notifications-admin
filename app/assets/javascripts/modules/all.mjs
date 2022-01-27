// JS Module used to combine all the JS modules used in the application into a single entry point,
// a bit like `app/__init__` in the Flask app.
//
// When processed by a bundler, this is turned into a Immediately Invoked Function Expression (IIFE)
// The IIFE format allows it to run in browsers that don't support JS Modules.
//
// Exported items will be added to the window.GOVUK namespace.
// For example, `export { Frontend }` will assign `Frontend` to `window.Frontend`

// GOVUK Frontend modules
import Header from 'govuk-frontend/components/header/header';
import Details from 'govuk-frontend/components/details/details';
import Button from 'govuk-frontend/components/button/button';
import Radios from 'govuk-frontend/components/radios/radios';

// Modules from 3rd party vendors
import morphdom from 'morphdom';

/**
 * TODO: Ideally this would be a NodeList.prototype.forEach polyfill
 * This seems to fail in IE8, requires more investigation.
 * See: https://github.com/imagitama/nodelist-foreach-polyfill
 */
function nodeListForEach (nodes, callback) {
  if (window.NodeList.prototype.forEach) {
    return nodes.forEach(callback)
  }
  for (var i = 0; i < nodes.length; i++) {
    callback.call(window, nodes[i], i, nodes);
  }
}

// Copy of the initAll function from https://github.com/alphagov/govuk-frontend/blob/v2.13.0/src/all.js
// except it only includes, and initialises, the components used by this application.
function initAll (options) {
  // Set the options to an empty object by default if no options are passed.
  options = typeof options !== 'undefined' ? options : {}

  // Allow the user to initialise GOV.UK Frontend in only certain sections of the page
  // Defaults to the entire document if nothing is set.
  var scope = typeof options.scope !== 'undefined' ? options.scope : document

  // Find all buttons with [role=button] on the scope to enhance.
  new Button(scope).init()

  // Find all global details elements to enhance.
  var $details = scope.querySelectorAll('details')
  nodeListForEach($details, function ($detail) {
    new Details($detail).init()
  })

  // Find first header module to enhance.
  var $toggleButton = scope.querySelector('[data-module="header"]')
  new Header($toggleButton).init()

  var $radios = scope.querySelectorAll('[data-module="radios"]')
  nodeListForEach($radios, function ($radio) {
    new Radios($radio).init()
  })
}

// Create separate namespace for GOVUK Frontend.
var Frontend = {
  "Header": Header,
  "Details": Details,
  "Button": Button,
  "initAll": initAll
}

var vendor = {
  "morphdom": morphdom
}

// The exported object will be assigned to window.GOVUK in our production code
// (bundled into an IIFE by RollupJS)
export {
  Frontend,
  vendor
}
