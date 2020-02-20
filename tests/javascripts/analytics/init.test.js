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

describe("Analytics init", () => {

  beforeAll(() => {

    window.ga = jest.fn();
    jest.spyOn(window.GOVUK.Analytics, 'load');

    // pretend we're on the /privacy page
    jest.spyOn(window, 'location', 'get').mockImplementation(() => {
      return {
        'pathname': '/privacy',
        'search': ''
      };
    });

  });

  afterEach(() => {

    window.GOVUK.Analytics.load.mockClear();
    window.ga.mockClear();

  });

  test("After the init.js script has been loaded, Google Analytics will be disabled", () => {

    expect(window['ga-disable-UA-75215134-1']).toBe(true);

  });

  describe("If initAnalytics has already been called", () => {

    beforeAll(() => {

      // Fake a tracker instance
      window.GOVUK.analytics = {};

    });

    beforeEach(() => {

      window.GOVUK.initAnalytics();

    });

    afterAll(() => {

      delete window.GOVUK.analytics;

    });

    test("The Google Analytics libraries will not be loaded", () => {

      expect(window.GOVUK.Analytics.load).not.toHaveBeenCalled();

    });

  });

  describe("If initAnalytics has not been called", () => {

    beforeEach(() => {

      window.GOVUK.initAnalytics();

    });

    afterEach(() => {

      // window.GOVUK.initAnalytics sets up a new window.GOVUK.analytics which needs clearing
      delete window.GOVUK.analytics;

    });

    test("Google Analytics will not be disabled", () => {

      expect(window['ga-disable-UA-75215134-1']).toBe(false);

    });

    test("The Google Analytics libraries will have been loaded", () => {

      expect(window.GOVUK.Analytics.load).toHaveBeenCalled();

    });

    test("There will be an interface with the Google Analytics API", () => {

      expect(window.GOVUK.analytics).toBeDefined();

    });

    test("A pageview will be registered", () => {

      expect(window.ga.mock.calls.length).toEqual(6);

      // The first 5 calls configure the analytics tracker. All subsequent calls send data
      expect(window.ga.mock.calls[5]).toEqual(['send', 'pageview', '/privacy']);

    });

  });

});
