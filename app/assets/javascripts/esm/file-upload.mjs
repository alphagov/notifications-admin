import { Button, isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

// Focus banners that do not use the GOVUK Design System Error Summary component but still need to
// match its behaviour when they appear

class FileUpload {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$form = $module;
    this.$field = this.$form.querySelector('.file-upload-field');
    this.$fieldErrors = this.$form.querySelector('.file-upload-label .govuk-error-message');

    // Note: label.file-upload-label, input.file-upload-field and button.file-upload-submit
    // are all hidden by CSS that uses the .govuk-frontend-supported class on the body tag

    this.addFakeButton();

    // Clear the form if the user navigates back to the page
    window.addEventListener("pageshow", () => this.$form.reset());


    this.$form.querySelector('.file-upload-field').addEventListener('change', () => {
      this.$form.submit();
      this.addCancelButton();
    });
  
  }

  addCancelButton() {
    const $cancelButton = document.createElement('a');
    $cancelButton.setAttribute('role', 'button');
    $cancelButton.setAttribute('href', '');
    $cancelButton.classList.add('file-upload-button', 'govuk-button', 'govuk-button--warning');
    $cancelButton.textContent = 'Cancel upload';

    this.$form.querySelector('button.file-upload-button').replaceWith($cancelButton);

    // add GOVUK Frontend behaviours
    new Button($cancelButton);

    // move focus to the cancel button, it is lost when the upload button is removed
    $cancelButton.focus();
  }

  addFakeButton() {
    const buttonText = this.$field.dataset.buttonText;
    const fieldId = this.$field.getAttribute('id'); // copy the id across so error links work
    const oldFieldId = `hidden-${fieldId}`;
    let buttonHTMLStr = `
        <button type="button" class="file-upload-button govuk-button govuk-!-margin-right-1" id="${fieldId}">
          ${buttonText}
        </button>`; // Styled as a submit button to raise prominence. The type shouldn't change.
    
    // If errors with the upload, copy into a label above the button
    // Buttons don't need labels by default as the accessible name comes from their text but
    // errors need to be added to that.
    const formErrors = Boolean(this.$fieldErrors);
    if (formErrors) {
      buttonHTMLStr = `
        <label class="file-upload-button-label govuk-error-message" for="${fieldId}">
          <span class="govuk-visually-hidden">${buttonText} </span>
          ${this.$fieldErrors.textContent}
        </label>
        ${buttonHTMLStr}`;
    }

    // Change id of field now we're using it for the button
    this.$field.setAttribute('id', oldFieldId);
    this.$field.parentNode.querySelector(`label[for=${fieldId}]`).setAttribute('for', oldFieldId);
    this.$field.insertAdjacentHTML('afterend', buttonHTMLStr);

    document.querySelector('button.file-upload-button').addEventListener('click', () => {
      this.$field.click();
    });
  }
}

export default FileUpload;
