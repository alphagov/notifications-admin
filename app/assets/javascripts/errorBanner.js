(function (window) {
  "use strict";

  /*
  This module is intended to be used to show and hide an error banner based on a javascript trigger. You should make
  sure the banner has an appropriate aria-live attribute, and a tabindex of -1 so that screenreaders and keyboard users
  are alerted to the change respectively.

  This may behave in unexpected ways if you have more than one element with the `banner-dangerous` class on your page.
  */
  window.GOVUK.ErrorBanner = {
    hideBanner: () => $('.banner-dangerous').addClass('govuk-!-display-none'),
    showBanner: () => $('.banner-dangerous')
      .removeClass('govuk-!-display-none')
      .trigger('focus'),
  };
})(window);
