(function(Modules) {
  "use strict";

  Modules.Autofocus = function() {
    this.start = function(component) {
      var $component = $(component),
          forceFocus = $component.data('forceFocus');

      // if the page loads with a scroll position, we can't assume the item to focus onload
      // is still where users intend to start
      if (($(window).scrollTop() > 0) && !forceFocus) { return; }

      // See if the component itself is something we want to send focus to
      var target = $component.filter('input, textarea, select');

      // Otherwise look inside the component to see if there are any elements
      // we want to send focus to
      if (target.length === 0) {
        target = $('input, textarea, select', $component);
      }

      target.eq(0).trigger('focus');

    };
  };

})(window.GOVUK.Modules);
