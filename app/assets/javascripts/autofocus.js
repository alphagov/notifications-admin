(function(Modules) {
  "use strict";

  Modules.Autofocus = function() {
    this.start = function(component) {

      $('input, textarea, select', component).eq(0).trigger('focus');

    };
  };

})(window.GOVUK.Modules);
