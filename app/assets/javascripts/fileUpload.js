(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    let $form;

    this.submit = () => $form.trigger('submit');

    this.start = function(component) {

      $form = $(component);

      // Clear the form if the user navigates back to the page
      $(window).on("pageshow", () => $form[0].reset());

      // Need to put the event on the container, not the input for it to work properly
      $form.on('change', '.file-upload-field', this.submit);

    };

  };

})(window.GOVUK.Modules);
