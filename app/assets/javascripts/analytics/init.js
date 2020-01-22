(function (window) {
  "use strict";

  window.GOVUK = window.GOVUK || {};

  const trackingId = 'UA-75215134-1';

  // Disable analytics by default
  window[`ga-disable-${trackingId}`] = true;

  const initAnalytics = function () {

    // guard against being called more than once
    if (!('analytics' in window.GOVUK)) {

      window[`ga-disable-${trackingId}`] = false;

      // Load Google Analytics libraries
      window.GOVUK.Analytics.load();

      // Configure profiles and make interface public
      // for custom dimensions, virtual pageviews and events
      window.GOVUK.analytics = new GOVUK.Analytics({
        trackingId: trackingId,
        cookieDomain: 'auto',
        anonymizeIp: true,
        allowAdFeatures: false,
        transport: 'beacon',
        expires: 365
      });

      // Track initial pageview
      window.GOVUK.analytics.trackPageview();

    }

  };

  window.GOVUK.initAnalytics = initAnalytics;
})(window);
