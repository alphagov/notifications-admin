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

  var renderIfComponentLosesFocus = ($options, $button, $focused) => () =>
    ($focused.attr('type') !== 'radio') &&
    render($options, $button) &&
    refocus($focused); // Make sure that window scrolls to focused element

  Modules.PaginatedOptions = function() {

    this.start = function(component) {

      let $component = $(component);
      let $options = $('label', $component);

      $component.append(
        $button = $('<input type="button" value="Later" class="tertiary-button" />')
      );

      $button.on('click', () =>
        $options.addClass('js-visible').has(':checked').focus() &&
        $button.removeClass('js-visible')
      );

      $component.on('keydown', 'input[type=radio]', function() {

        // intercept keypresses which aren’t enter or space
        if (event.which !== 13 && event.which !== 32) {
          setTimeout(
            renderIfComponentLosesFocus($options, $button, $(document.activeElement)),
            200
          );
          return true;
        }

        event.preventDefault();

        render($options, $button);
        refocus($(this));

      });

      $component.on('click', 'input[type=radio]', function(event) {

        deselectUnchecked($options);

        // stop click being triggered by keyboard events
        if (!event.pageX) return true;

        render($options, $button);
        refocus($(this));

      });

      render($options, $button);

    };

  };

})(window.GOVUK.Modules);
