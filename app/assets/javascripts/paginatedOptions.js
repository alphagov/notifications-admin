(function(Modules) {

  "use strict";

  var filterOptionVisibility = $options => $options
    .removeClass('js-visible')
    .filter(
      (index, element) => (index === 0 || $(element).has(':checked').length)
    )
    .addClass('js-visible');

  Modules.PaginatedOptions = function() {

    this.start = function(component) {

      let $component = $(component);
      let $options = $('label', $component);
      let $button = $('<input type="button" value="Later" class="tertiary-button js-visible" />');

      $component.append($button);

      filterOptionVisibility($options);

      $button.on('click', function() {
        $options.addClass('js-visible').has(':checked').focus();
        $button.removeClass('js-visible');
      });

      $component.on('change', 'input[type=radio]', function() {

        $(this).trigger('focus');

      });

      $(document).on('focus', '*', function(event) {

        console.log('focus', $(this));

        return;

        console.log('blur', $component.find(':focus'));

        if ($component.find(':focus').length > 0) return true;

        filterOptionVisibility($options);

        $button.addClass('js-visible');

        if ($options.has(':checked').find('input').attr('id') === $options.eq(0).find('input').attr('id')) {
          $button.prop('value', 'Later');
        } else {
          $button.prop('value', 'Choose a different time');
        }

        return true;

      });

      $component.on('click', 'input[type=radio]', function(event) {

        // Workaround because GOV.UK SelectionButtons doesn’t deselect in this case
        $options.filter((index, element) => $(element).not(':has(:checked)')).removeClass('selected');
        console.log('click', event.pageX);
        if (!event.pageX) return;

        filterOptionVisibility($options);

        $button.addClass('js-visible');

        if ($options.has(':checked').find('input').attr('id') === $options.eq(0).find('input').attr('id')) {
          $button.prop('value', 'Later');
        } else {
          $button.prop('value', 'Choose a different time');
        }

      });

    };

  };

})(window.GOVUK.Modules);
