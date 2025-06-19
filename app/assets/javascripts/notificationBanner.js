(function(window) {
  "use strict";

  // Based on GOVUK.ErrorBanner
  window.GOVUK.NotificationBanner = {
    hideBanner: () => $('.govuk-notification-banner').addClass('govuk-!-display-none'),
    showBanner: () =>
        $('.govuk-notification-banner')
            .removeClass('govuk-!-display-none')
            .trigger('focus')
  };
})(window);
