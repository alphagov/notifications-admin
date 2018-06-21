(function(Modules) {
  "use strict";

  Modules.ConditionalRadios = function() {

    this.start = function(component) {

      const $radios = $('[type=radio]', $(component)),
            $checkboxes = $('[type=checkbox]', $(component));

      let clearable = true;

      let clearInvalidSelections = function() {
        if (!clearable) {
          clearable = true;
          return;
        }
        $radios.each(function() {
          let checked = $(this).is(':checked');
          $('#panel-' + $(this).attr('value'))
            .each(function() {
              if (!checked) {
                $('[type=checkbox]', this).removeAttr('checked');
              }
            });
        });
      };

      let selectParent = function() {
        clearable = false;
        let parentValue = $(this).parents("[id^='panel-']").attr('id').replace('panel-', '');
        $('[value=' + parentValue + ']').trigger('click');
      };

      $checkboxes.on('click', selectParent);
      $radios.on('click', clearInvalidSelections);
      clearInvalidSelections();

    };
  };

})(window.GOVUK.Modules);
