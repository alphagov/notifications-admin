(function(Modules) {
  "use strict";

  Modules.Autofocus = function() {
    this.start = function(component) {
      var $component = $(component),
          forceFocus = $component.data('forceFocus');

      // if the page loads with a scroll position, we can't assume the item to focus onload
      // is still where users intend to start
      if (($(window).scrollTop() > 0) && !forceFocus) { return; }

      $component.filter('input, textarea, select').eq(0).trigger('focus');

    };
  };

})(window.GOVUK.Modules);
