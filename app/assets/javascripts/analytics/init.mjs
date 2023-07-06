import { Analytics } from './analytics.mjs';

const trackingId = 'UA-75215134-1';

let analytics = null; // variable to store analytics instances in, defaulted to off

// Disable analytics by default
window[`ga-disable-${trackingId}`] = true;

const initAnalytics = function () {

  // guard against being called more than once
  if (analytics !== null) {

    window[`ga-disable-${trackingId}`] = false;

    // Load Google Analytics libraries
    Analytics.load();

    // Configure profiles and make interface public
    // for custom dimensions, virtual pageviews and events
    analytics = new Analytics({
      trackingId: trackingId,
      cookieDomain: 'auto',
      anonymizeIp: true,
      allowAdFeatures: false,
      transport: 'beacon',
      expires: 365
    });

    // Track initial pageview
    analytics.trackPageview();

  }

};

export { initAnalytics, analytics }
