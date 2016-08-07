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

      $component.on('click', 'label', function() {

        // Workaround because GOV.UK SelectionButtons doesn’t deselect in this case
        $options.filter((index, element) => $(element).not(':has(:checked)')).removeClass('selected');

        filterOptionVisibility($options);

        $button.addClass('js-visible');

        if ($options.has(':checked').find('input').attr('id') === $options.eq(0).find('input').attr('id')) {
          $button.prop('value', 'Later');
        } else {
          $button.prop('value', 'Choose a different time');
        }

        $options.has(':checked').focus();

      });

    };

  };

})(window.GOVUK.Modules);
