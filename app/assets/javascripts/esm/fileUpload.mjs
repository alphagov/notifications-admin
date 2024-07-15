import { Button } from "govuk-frontend"
export class FileUpload {
  constructor($module) {
    if (!$module  ||
        !document.body.classList.contains('govuk-frontend-supported')) {
        return this
      }
    this.$module = $module
    this.addCancelButton()
  }

  addCancelButton() {

    const $cancelButton = document.createElement("a");
    
    $cancelButton.setAttribute('href','')
    $cancelButton.setAttribute('role','button')
    $cancelButton.setAttribute('class','file-upload-button govuk-button govuk-button--warning')
    $cancelButton.text = 'Cancel upload'


    this.$module.append($cancelButton);

    // add GOVUK Frontend behaviours
    new Button($cancelButton);

    // move focus to the cancel button, it is lost when the upload button is removed
    $cancelButton.focus();

  };
}