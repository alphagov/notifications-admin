(function(global) {

  "use strict";

  global.GOVUK.Modules.RadioSlider = function() {

    this.start = function(component) {

      $(component)
        .on('click', function() {

          leftRight = $(this).find(':checked').next('label').text().split('/');

          if (leftRight.length === 2) {
            $(this).find('.radio-slider-left-value').html(leftRight[0]);
            $(this).find('.radio-slider-right-value').html(leftRight[1]);
          }

        })
        .trigger('click');

    };

  };

})(window);
