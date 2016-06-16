(function(Modules) {
  "use strict";

  Modules.CharacterCount = function() {

    this.start = function(component) {

      var getCharacterCount = () =>
        ($textarea.val()).length;

      var getLengthOfOneMessage = () =>
        160 - (serviceName + ': ').length;

      var $component = $(component);

      var serviceName = $component.data('service-name');

      var $textarea = $('textarea', $component)
        .eq(0)
        .on('change keyup paste', () => $counter.html(`
          ${getCharacterCount()} of ${getLengthOfOneMessage()} characters
        `));

      $component
        .append($counter = $(`
          <p class="textbox-character-count"
            role="status" aria-live="polite" aria-relevant="text"
            id="word-count-${$textarea.prop('name')}"
          />
        `));

      $textarea
        .trigger('change');

    };

  };

})(window.GOVUK.Modules);
