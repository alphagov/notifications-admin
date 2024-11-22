// GOVUK Frontend modules
import { createAll, Header, Button, Radios, ErrorSummary, SkipLink, Tabs, NotificationBanner } from 'govuk-frontend';

import CollapsibleCheckboxes from './collapsible-checkboxes.mjs';
import FocusBanner from './focus-banner.mjs';
import ColourPreview from './colour-preview.mjs';
import FileUpload from './file-upload.mjs';
import Autofocus from './autofocus.mjs';
import Homepage from './homepage.mjs';
import PreviewPane from './preview-pane.mjs';
import CopyToClipboard from './copy-to-clipboard.mjs';
import ListEntry from './list-entry.mjs';

// Modules from 3rd party vendors
import morphdom from 'morphdom';

createAll(Button);
createAll(Header);
createAll(Radios);
createAll(ErrorSummary);
createAll(SkipLink);
createAll(Tabs);
createAll(NotificationBanner);

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

const $autoFocus = document.querySelector('[data-notify-module="autofocus"]');
if ($autoFocus) {
  new Autofocus($autoFocus);
}

const $homePage = document.querySelector('[data-notify-module="homepage"]');
if ($homePage) {
  new Homepage($homePage);
}

// this module doesn't currently use "data-notify-module" for initialisation
// should we change that?
const $previewPane = document.querySelector('.govuk-radios__item input[name="branding_style"]:checked');
if ($previewPane) {
  new PreviewPane($previewPane);
}

const $CopyToClipboardArray = document.querySelectorAll('[data-notify-module="copy-to-clipboard"]');
if ($CopyToClipboardArray.length > 0) {
  $CopyToClipboardArray.forEach((el) => new CopyToClipboard(el));
}

const $ListEntryArray = document.querySelectorAll('[data-notify-module="list-entry"]');
if ($ListEntryArray.length > 0) {
  $ListEntryArray.forEach((el) => new ListEntry(el));
}

const focusBanner = new FocusBanner();

// ES modules do not export to global so in order to
// reuse some of teh import here in our other
// global functions, we need to explicitly attach them to window
// this will be removed when we migrate out files
// to ES modules

// for UpdateContent.js
window.Morphdom = morphdom;
