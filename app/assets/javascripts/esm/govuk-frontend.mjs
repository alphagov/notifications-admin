import { createAll, Header, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';
import { FileUpload } from './fileUpload.mjs'

createAll(Button)
createAll(Header)
createAll(Radios)
createAll(ErrorSummary)
createAll(SkipLink)
createAll(Tabs)

// for fileUpload.js
window.GOVUKButton = Button

const $fileUpload = document.querySelector('[data-notify-module="file-upload"]')
if ($fileUpload) {
    new FileUpload($fileUpload)
}

