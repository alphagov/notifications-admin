(function(Modules) {
  "use strict";

  Modules.ConditionalRadios = function() {

    this.start = function(component) {

      const $radios = $('[type=radio]', $(component)),
            showHidePanels = function() {
              $radios.each(function() {
                $('#panel-' + $(this).attr('value'))
                  .toggleClass(
                    'js-hidden',
                    !$(this).is(":checked")
                  );
              });
            };

      $radios.on('click', showHidePanels);
      showHidePanels();

    };
  };

})(window.GOVUK.Modules);
