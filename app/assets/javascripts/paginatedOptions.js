(function(Modules) {

  "use strict";

  var render = ($options, $button) => (
    filterOptionVisibility($options) && setButtonState($options, $button)
  );

  var filterOptionVisibility = $options => $options
    .removeClass('js-visible')
    .filter(
      (index, element) => (index === 0 || $(element).has(':checked').length)
    )
    .addClass('js-visible');

  var setButtonState = ($options, $button) => $button
    .addClass('js-visible')
    .prop(
      'value',
      $options.has(':checked').find('input').attr('id') === $options.eq(0).find('input').attr('id') ?
        'Later' : 'Choose a different time'
    );

  // Workaround because GOV.UK SelectionButtons doesn’t deselect in this case
  var deselectUnchecked = $options => $options
    .filter(
      (index, element) => $(element).not(':has(:checked)')
    ).removeClass('selected');

  var refocus = $element => setTimeout(
    () => $element.blur().trigger('focus'),
    10
  );

  Modules.PaginatedOptions = function() {

    this.start = function(component) {

      let $component = $(component);
      let $options = $('label', $component);

      $component.append(
        $button = $('<input type="button" value="Later" class="tertiary-button" />')
      );

      render($options, $button);

      $button.on('click', () =>
        $options.addClass('js-visible').has(':checked').focus() &&
        $button.removeClass('js-visible')
      );

      $component.on('focusout', () =>
        setTimeout(
          () => ($(document.activeElement).attr('type') !== 'radio') && render($options, $button),
          200
        )
      );

      $component.on('keydown', 'input[type=radio]', function() {

        if (event.which !== 13 && event.which !== 32) return true;

        event.preventDefault();

        render($options, $button);
        refocus($(this));

      });

      $component.on('click', 'input[type=radio]', function(event) {

        deselectUnchecked($options);

        // only trigger click on mouse events
        if (!event.pageX) return true;

        render($options, $button);
        refocus($(this));

      });

    };

  };

})(window.GOVUK.Modules);
