(function (window) {
  "use strict";

  window.GOVUK = window.GOVUK || {};

  // Stripped-down wrapper for Google Analytics, based on:
  // https://github.com/alphagov/static/blob/master/app/assets/javascripts/analytics_toolkit/analytics.js
  const Analytics = function (config) {
    window.ga('create', config.trackingId, config.cookieDomain);

    window.ga('set', 'anonymizeIp', config.anonymizeIp);
    window.ga('set', 'displayFeaturesTask', config.displayFeaturesTask);
    window.ga('set', 'transport', config.transport);

  };

  Analytics.load = function () {
    /* jshint ignore:start */
    (function(i, s, o, g, r, a, m){ i['GoogleAnalyticsObject'] = r; i[r] = i[r] || function () {
      (i[r].q = i[r].q || []).push(arguments) }, i[r].l = 1 * new Date(); a = s.createElement(o),
      m = s.getElementsByTagName(o)[0]; a.async = 1; a.src = g; m.parentNode.insertBefore(a,m)
    })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
    /* jshint ignore:end */

  };

  Analytics.prototype.trackPageview = function (path, title, options) {

    // strip UUIDs
    const page = (window.location.pathname + window.location.search).replace(
      /[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}/g, '…'
    );
    window.ga('send', 'pageview', page);

  };

  window.GOVUK.Analytics = Analytics;

})(window);
