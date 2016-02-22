(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    let $field;

    this.submit = function() {

      $field.parents('form').trigger('submit');

    };

    this.start = function(component) {

      $field = $('.file-upload-field', component);

      // Need to put the event on the container, not the input for it to work properly
      $(component).on('change', '.file-upload-field', this.submit);

    };

  };

})(window.GOVUK.Modules);
