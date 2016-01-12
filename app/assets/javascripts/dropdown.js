(function(Modules) {
  "use strict";

  Modules.Dropdown = function() {

    this.start = function(component) {

      $('.dropdown-toggle', component)
        .on(
          'click', () => $(component).toggleClass('js-closed')
        )
        .trigger('click');

    };

  };

})(window.GOVUK.Modules);
