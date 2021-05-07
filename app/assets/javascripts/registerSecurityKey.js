(function(window) {
  "use strict";

  window.GOVUK.Modules.RegisterSecurityKey = function() {
    this.start = function(component) {

      $(component)
        .on('click', function(event) {
          event.preventDefault();
          alert('not implemented');
        });
    };
  };
})(window);
