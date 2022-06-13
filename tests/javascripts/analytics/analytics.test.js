const helpers = require('../support/helpers');

beforeAll(() => {

  // add the script GA looks for in the document
  document.body.appendChild(document.createElement('script'));

  require('../../../app/assets/javascripts/govuk/cookie-functions.js');
  require('../../../app/assets/javascripts/analytics/analytics.js');
  require('../../../app/assets/javascripts/analytics/init.js');

});

afterAll(() => {

  require('../support/teardown.js');

});

describe("Analytics", () => {

  let analytics;

  beforeEach(() => {

    window.ga = jest.fn();

    analytics = new GOVUK.Analytics({
      trackingId: 'UA-75215134-1',
      cookieDomain: 'auto',
      anonymizeIp: true,
      allowAdFeatures: false,
      transport: 'beacon',
      expires: 365
    });

  });

  afterEach(() => {

    window.ga.mockClear();

  });

  describe("When created", () => {

    test("It configures a tracker", () => {

      setUpArguments = window.ga.mock.calls;

      expect(setUpArguments[0]).toEqual(['create', {
       'trackingId': 'UA-75215134-1', 'cookieDomain': 'auto', 'cookieExpires': 31536000, "cookieFlags": "Secure; SameSite=Lax",
      }]);
      expect(setUpArguments[1]).toEqual(['set', 'anonymizeIp', true]);
      expect(setUpArguments[2]).toEqual(['set', 'allowAdFeatures', false]);
      expect(setUpArguments[3]).toEqual(['set', 'transport', 'beacon']);
      expect(setUpArguments[4]).toEqual(['set', 'title', 'GOV.UK Notify']);

    });

  });

  describe("When tracking pageviews", () => {

    beforeEach(() => {

      // clear calls to window.ga from set up
      window.ga.mockClear();

    });

    test("It sends the right URL for the page if no arguments", () => {

      jest.spyOn(window, 'location', 'get').mockImplementation(() => {
        return {
          'pathname': '/privacy',
          'search': ''
        };
      });

      analytics.trackPageview();

      expect(window.ga.mock.calls[0]).toEqual(['send', 'pageview', '/privacy']);

    });

    test("It strips the UUIDs from URLs", () => {

      jest.spyOn(window, 'location', 'get').mockImplementation(() => {
        return {
          'pathname': '/services/6658542f-0cad-491f-bec8-ab8457700ead',
          'search': ''
        };
      });

      analytics.trackPageview();

      expect(window.ga.mock.calls[0]).toEqual(['send', 'pageview', '/services/…']);

    });

  });

  describe("When tracking events", () => {

    beforeEach(() => {

      // clear calls to window.ga from set up
      window.ga.mockClear();

    });

    test("It sends the right arguments to `ga`", () => {

      analytics.trackEvent('Error', 'Enter a valid email address', {
        'label': 'email_address'
      });

      expect(window.ga.mock.calls[0]).toEqual(['send', 'event', {
        'eventCategory': 'Error',
        'eventAction': 'Enter a valid email address',
        'eventLabel': 'email_address'
      }]);

    });

  });

});
