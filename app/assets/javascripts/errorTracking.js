(function(window) {
  "use strict";

  window.GOVUK.Modules.TrackError = function() {

    this.start = function(component) {

      if (!('analytics' in window.GOVUK)) return;

      window.GOVUK.analytics.trackEvent(
        'Error',
        $(component).data('error-type'),
        {
          'label': $(component).data('error-label')
        }
      );

    };

  };

})(window);
