(function(Modules) {
  "use strict";

  Modules.Autofocus = function() {
    this.start = function(component) {
      var $component = $(component),
          forceFocus = $component.data('forceFocus'),
          labelText = $('label[for="' + $component.attr('id') + '"]').eq(0).text().trim(),
          clearAriaLabel = evt => {
            $component.removeAttr('aria-label');
            $component.off('blur', clearAriaLabel);
          };

      // if the page loads with a scroll position, we can't assume the item to focus onload
      // is still where users intend to start
      if (($(window).scrollTop() > 0) && !forceFocus) { return; }

      // screenreaders announce the page title when a new page loads
      // this will be lost when focus is moved to our form control so add it to the label instead
      $component.attr('aria-label', document.title + ' - ' + labelText);

      $component.filter('input, textarea, select').eq(0).trigger('focus');

      // the page title prefix is only needed on page load so remove once focus has shifted
      $component.on('blur', clearAriaLabel);

    };
  };

})(window.GOVUK.Modules);
