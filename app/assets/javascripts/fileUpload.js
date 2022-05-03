(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    this.submit = () => this.$form.trigger('submit');

    this.showCancelButton = () => $('.file-upload-button', this.$form).replaceWith(`
      <a href="" class='govuk-button govuk-button--warning govuk-!-margin-right-1'>Cancel upload</a>
    `);

    // Add a button that passes a click to the input[type=file]
    this.addFakeButton = function () {
      $(
        '<button type="button" class="govuk-button govuk-!-margin-right-1">' +
          this.$field.data('buttonText') +
        '</button>'
      )
      .on('click', e => this.$field.click())
      .insertAfter(this.$field);
    };

    this.start = function(component) {

      this.$form = $(component);
      this.$field = this.$form.find('.file-upload-field');

      // Hide all controls except the button, semantically and visually
      // These elements are also hidden in their CSS to override any use of the display style
      this.$form.find('.file-upload-label, .file-upload-submit')
                .add(this.$field)
                .attr('hidden', "");

      this.addFakeButton();

      // Clear the form if the user navigates back to the page
      $(window).on("pageshow", () => this.$form[0].reset());

      // Need to put the event on the container, not the input for it to work properly
      this.$form.on(
        'change', '.file-upload-field',
        () => this.submit() && this.showCancelButton()
      );

    };

  };

})(window.GOVUK.Modules);
