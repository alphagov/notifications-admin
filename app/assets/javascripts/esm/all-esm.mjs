// GOVUK Frontend modules
import { createAll, Header, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

import CollapsibleCheckboxes from './collapsible-checkboxes.mjs';

// Modules from 3rd party vendors
import morphdom from 'morphdom';

createAll(Button)
createAll(Header)
createAll(Radios)
createAll(ErrorSummary)
createAll(SkipLink)
createAll(Tabs)

const $collapsibleCheckboxes = document.querySelector('[data-notify-module="collapsible-checkboxes"]')
  if ($collapsibleCheckboxes) {
    new CollapsibleCheckboxes($collapsibleCheckboxes)
  }


// ES modu;es do not export to global so in order to
// reuse some of teh import here in our other 
// global functions, we need to explicitly attach them to window
// this will be removed when we migrate out files
// to ES modules

// for fileUpload.js
window.GOVUKFrontendButton = Button;

// for UpdateContent.js
window.Morphdom = morphdom;
