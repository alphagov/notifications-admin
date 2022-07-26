(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    this.submit = () => this.$form.trigger('submit');

    this.addCancelButton = () => {

      var $cancelButton = $(`
        <a href="" role="button" class="file-upload-button govuk-button govuk-button--warning">
          Cancel upload
        </a>
      `);

      $('button[type=button]', this.$form).replaceWith($cancelButton);

      // add GOVUK Frontend behaviours
      new window.GOVUK.Frontend.Button(this.$form[0]).init();

      // move focus to the cancel button, it is lost when the upload button is removed
      $cancelButton.focus();

    };

    // Add a button that passes a click to the input[type=file]
    this.addFakeButton = function () {

      var buttonText = this.$field.data('buttonText');
      var buttonHTMLStr = `
        <button type="button" class="file-upload-button govuk-button govuk-!-margin-right-1" id="file-upload-button">
          ${buttonText}
        </button>`;

      // If errors with the upload, copy into a label above the button
      // Buttons don't need labels by default as the accessible name comes from their text but
      // errors need to be added to that.
      if (this.$fieldErrors.length > 0) {
        buttonHTMLStr = `
          <label class="file-upload-button-label error-message" for="file-upload-button">
            <span class="govuk-visually-hidden">${buttonText} </span>
            ${this.$fieldErrors.eq(0).text()}
          </label>
          ${buttonHTMLStr}`;
      }

      $(buttonHTMLStr)
      .on('click', e => this.$field.click())
      .insertAfter(this.$field);

    };

    this.start = function(component) {

      this.$form = $(component);
      this.$field = this.$form.find('.file-upload-field');
      this.$fieldErrors = this.$form.find('.file-upload-label .error-message');

      // Note: label.file-upload-label, input.file-upload-field and button.file-upload-submit
      // are all hidden by CSS that uses the .js-enabled class on the body tag

      this.addFakeButton();

      // Clear the form if the user navigates back to the page
      $(window).on("pageshow", () => this.$form[0].reset());

      // Need to put the event on the container, not the input for it to work properly
      this.$form.on(
        'change', '.file-upload-field',
        () => this.submit() && this.addCancelButton()
      );

    };

  };

})(window.GOVUK.Modules);
