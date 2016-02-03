(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    let $field, $button, $filename;

    this.update = function() {

      $filename.text($field.val().split('\\').pop());

    };

    this.start = function(component) {

      $field = $('.file-upload-field', component);
      $button = $('.file-upload-button', component);
      $filename = $('.file-upload-filename', component);

      // Need to put the event on the container, not the input for it to work properly
      $(component).on('change', '.file-upload-field', this.update);

    };

  };

})(window.GOVUK.Modules);
