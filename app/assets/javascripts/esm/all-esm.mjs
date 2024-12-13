// GOVUK Frontend modules
import { createAll, Header, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

import CollapsibleCheckboxes from './collapsible-checkboxes.mjs';
import FocusBanner from './focus-banner.mjs';
import ColourPreview from './colour-preview.mjs';
import FileUpload from './file-upload.mjs';

// Modules from 3rd party vendors
import morphdom from 'morphdom';

createAll(Button);
createAll(Header);
createAll(Radios);
createAll(ErrorSummary);
createAll(SkipLink);
createAll(Tabs);

const $collapsibleCheckboxes = document.querySelector('[data-notify-module="collapsible-checkboxes"]');
if ($collapsibleCheckboxes) {
  new CollapsibleCheckboxes($collapsibleCheckboxes);
}

const $colourPreview = document.querySelector('[data-notify-module="colour-preview"]');
if ($colourPreview) {
  new ColourPreview($colourPreview);
}

const $fileUpload = document.querySelector('[data-notify-module="file-upload"]');
if ($fileUpload) {
  new FileUpload($fileUpload);
}

const focusBanner = new FocusBanner();

// ES modules do not export to global so in order to
// reuse some of teh import here in our other
// global functions, we need to explicitly attach them to window
// this will be removed when we migrate out files
// to ES modules

// for UpdateContent.js
window.Morphdom = morphdom;
