(function(Modules) {
  "use strict";

  Modules.TrackError = function() {

    this.start = function(component) {

      if (!ga) return;

      ga(
        'send',
        'event',
        'Error',
        $(component).data('error-type'),
        $(component).data('error-label')
      );

    };

  };

})(window.GOVUK.Modules);
