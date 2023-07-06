// JS Module used to combine all the JS modules used in the application into a single entry point,
// a bit like `app/__init__` in the Flask app.
//
// When processed by a bundler, this is turned into a Immediately Invoked Function Expression (IIFE)
// The IIFE format allows it to run in browsers that don't support JS Modules.
//
// Exported items will be added to the window.GOVUK namespace.
// For example, `export { Frontend }` will assign `Frontend` to `window.Frontend`

import 'jquery'; // adds $ and jQuery as global variables
import 'timeago'; // adds the timeago plugin to the jQuery (and $) object(s)

// GOVUK Frontend modules
import { Header, Details, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

// JS custom to this application
import { ShowHideContent } from '../govuk-frontend-toolkit/show-hide-content.mjs';
import { cookie, getCookie, setCookie, getConsentCookie } from '../govuk/cookie-functions.mjs';
import { initAnalytics } from '../analytics/init.mjs';
import { hasConsentFor } from '../consent.mjs';
import { notifyModules } from '../modules.mjs';
import { stickAtTopWhenScrolling, stickAtBottomWhenScrolling } from '../stick-to-window-when-scrolling.mjs';
import { disableSubmitButtons } from '../preventDuplicateFormSubmissions.mjs';


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
  var $details = scope.querySelectorAll('[data-module="govuk-details"]')
  nodeListForEach($details, function ($detail) {
    new Details($detail).init()
  })

  // Find first header module to enhance.
  var $toggleButton = scope.querySelector('[data-module="govuk-header"]')
  new Header($toggleButton).init()

  var $radios = scope.querySelectorAll('[data-module="govuk-radios"]')
  nodeListForEach($radios, function ($radio) {
    new Radios($radio).init()
  })

  var $skipLinks = scope.querySelectorAll('[data-module="govuk-skip-link"]')
  nodeListForEach($skipLinks, function ($skipLink) {
    new SkipLink($skipLink).init()
  })

  var $tabs = scope.querySelectorAll('[data-module="govuk-tabs"]')
  nodeListForEach($tabs, function ($tabs) {
    new Tabs($tabs).init()
  })

  // There will only every be one error-summary per page
  var $errorSummary = scope.querySelector('[data-module="govuk-error-summary"]')
  new ErrorSummary($errorSummary).init()
}

// Create separate namespace for GOVUK Frontend.
var Frontend = {
  "Header": Header,
  "Details": Details,
  "Button": Button,
  "Radios": Radios,
  "ErrorSummary": ErrorSummary,
  "SkipLink": SkipLink,
  "initAll": initAll
}

// Initialise 3rd party scripts
$(() => $("time.timeago").timeago());

// Execute the code for any modules which add to NotifyModules
import '../cookieMessage.mjs';
import '../cookieSettings.mjs';
import '../copyToClipboard.mjs';
import '../autofocus.mjs';
import '../enhancedTextbox.mjs';
import '../fileUpload.mjs';
import '../radioSelect.mjs';
import '../updateContent.mjs';
import '../listEntry.mjs';
import '../liveSearch.mjs';
import '../errorTracking.mjs';
import '../fullscreenTable.mjs';
import '../radios-with-images.mjs';
import '../colourPreview.mjs';
import '../liveCheckboxControls.mjs';
import '../templateFolderForm.mjs';
import '../addBrandingOptionsForm.mjs';
import '../setAuthTypeForm.mjs';
import '../collapsibleCheckboxes.mjs';
import '../errorBanner.mjs';
import '../registerSecurityKey.mjs';
import '../authenticateSecurityKey.mjs';
import '../updateStatus.mjs';
import '../homepage.mjs';

// Run any modules without exports
import '../previewPane.mjs';

Frontend.initAll();

var consentData = getConsentCookie();
NotifyModules.CookieBanner.clearOldCookies(consentData);

if (hasConsentFor('analytics', consentData)) {
  initAnalytics();
}

stickAtTopWhenScrolling.init()
stickAtBottomWhenScrolling.init();

var _showHideContent = new GOVUK.ShowHideContent();
_showHideContent.init();

$('form').on('submit', disableSubmitButtons);

notifyModules.start()

// inline scripts
$(() => $('.error-message, .govuk-error-message').eq(0).parent('label').next('input').trigger('focus'));

$(() => $('.banner-dangerous').eq(0).trigger('focus'));

$(() => $('.govuk-header__container').on('click', function() {
  $(this).css('border-color', '#1d70b8');
}));

// Applies our expanded focus style to the siblings of links when that link is wrapped in a heading.
//
// This will be possible in CSS in the future, using the :has pseudo-class. When :has is available
// in the browsers we support, this code can be replaced with a CSS-only solution.
$('.js-mark-focus-on-parent').on('focus blur', '*', e => {
  $target = $(e.target);
  if (e.type === 'focusin') {
    $target.parent().addClass('js-child-has-focus');
  } else {
    $target.parent().removeClass('js-child-has-focus');
  }
});


// The exported object will be assigned to window.GOVUK in our production code
// (bundled into an IIFE by RollupJS)
export {
  Frontend
}
