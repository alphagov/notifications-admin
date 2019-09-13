(function() {

  "use strict";

  let disableSubmitButtons = function(event) {

    var $submitButton = $(this).find(':submit');

    if ($submitButton.data('clicked') == 'true') {

      event.preventDefault();

    } else {

      $submitButton.data('clicked', 'true');
      setTimeout(renableSubmitButton($submitButton), 1500);

    }

  };

  let renableSubmitButton = $submitButton => () => {

    $submitButton.data('clicked', '');

  };

  $('form').on('submit', disableSubmitButtons);

})();
