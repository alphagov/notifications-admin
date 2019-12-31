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
      displayFeaturesTask: null,
      transport: 'beacon'
    });

  });

  afterEach(() => {

    window.ga.mockReset();

  });

  describe("When created", () => {

    test("It configures a tracker", () => {

      setUpArguments = window.ga.mock.calls;

      expect(setUpArguments[0]).toEqual(['create', 'UA-75215134-1', 'auto']);
      expect(setUpArguments[1]).toEqual(['set', 'anonymizeIp', true]);
      expect(setUpArguments[2]).toEqual(['set', 'displayFeaturesTask', null]);
      expect(setUpArguments[3]).toEqual(['set', 'transport', 'beacon']);

    });

  });

  describe("When tracking pageviews", () => {

    test("It sends the right URL for the page if no arguments", () => {

      window.ga.mockClear();

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

      window.ga.mockClear();

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

});
