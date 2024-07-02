import { Header, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

var options = typeof options !== 'undefined' ? options : {}

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