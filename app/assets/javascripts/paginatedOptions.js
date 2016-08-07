(function(Modules) {

  "use strict";

  Modules.PaginatedOptions = function() {

    this.start = function(component) {

      console.log('hi');

      let $component = $(component);
      let $options = $('label', $component);
      let $button = $('.tertiary-button', $component);
      let containerWidth = $component.width() - $button.outerWidth();
      let runningWidth = 0, i = 0, newWidth;

      while (i <= $options.length) {
        runningWidth = runningWidth + $options.eq(i++).outerWidth(true);
        if (runningWidth > containerWidth) break;
      }

      $component.width(runningWidth);

      $button.on('click', function() {
        $options.eq(0).css('margin-left', $options.eq(0).outerWidth(true) * -1);
      });

    };

  };

})(window.GOVUK.Modules);
