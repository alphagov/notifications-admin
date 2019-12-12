(function(global) {

  "use strict";

  global.GOVUK.Modules.RadioSlider = function() {

    this.start = function(component) {

      $(component)
        .on('click', function() {

          valuesInLabel = $(this).find(':checked').next('label').text().split('/');

          if (valuesInLabel.length === 2) {
            leftValue = valuesInLabel[0];
            rightValue = valuesInLabel[1];
            $(this).find('.radio-slider-left-value').html(leftValue);
            $(this).find('.radio-slider-right-value').html(rightValue);
          }

        })
        .trigger('click');

    };

  };

})(window);
