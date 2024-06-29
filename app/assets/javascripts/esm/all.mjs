// JS Module used to combine all the JS modules used in the application into a single entry point,
// a bit like `app/__init__` in the Flask app.
//
// When processed by a bundler, this is turned into a Immediately Invoked Function Expression (IIFE)
// The IIFE format allows it to run in browsers that don't support JS Modules.
//
// Exported items will be added to the window.GOVUK namespace.
// For example, `export { Frontend }` will assign `Frontend` to `window.Frontend`

// GOVUK Frontend modules
import { Header, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

// Modules from 3rd party vendors
import morphdom from 'morphdom';

// Copy of the initAll function from https://github.com/alphagov/govuk-frontend/blob/v2.13.0/src/all.js
// except it only includes, and initialises, the components used by this application.
function initAll (options) {
  // Set the options to an empty object by default if no options are passed.
  options = typeof options !== 'undefined' ? options : {}

  // Allow the user to initialise GOV.UK Frontend in only certain sections of the page
  // Defaults to the entire document if nothing is set.
  var scope = typeof options.scope !== 'undefined' ? options.scope : document

  // Find all buttons with [role=button] on the scope to enhance.
  var $buttons = scope.querySelectorAll('[data-module="govuk-button"]')
  if ($buttons) {
    $buttons.forEach(($button) => {
      new Button($button)
    })
  }

  // Find first header module to enhance.
  var $toggleButton = scope.querySelector('[data-module="govuk-header"]')
  new Header($toggleButton)

  var $radios = scope.querySelectorAll('[data-module="govuk-radios"]')
  if ($radios) {
    $radios.forEach(($radio) => {
      new Radios($radio)
    })
  }

  var $skipLinks = scope.querySelectorAll('[data-module="govuk-skip-link"]')
  if ($skipLinks) {
    $skipLinks.forEach(($skipLink) => {
      new SkipLink($skipLink)
    })
  }

  var $tabs = scope.querySelectorAll('[data-module="govuk-tabs"]')
  if ($tabs) {
    $tabs.forEach(($tabs) => {
      new Tabs($tabs)
    })
  }

  // There will only every be one error-summary per page
  var $errorSummary = scope.querySelector('[data-module="govuk-error-summary"]');
  if ($errorSummary) {
    new ErrorSummary($errorSummary);
  }
}

// Create separate namespace for GOVUK Frontend.
var Frontend = {
  "Header": Header,
  "Button": Button,
  "Radios": Radios,
  "ErrorSummary": ErrorSummary,
  "SkipLink": SkipLink,
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
