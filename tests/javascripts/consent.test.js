const helpers = require('./support/helpers');

beforeAll(() => {

  require('../../app/assets/javascripts/govuk/cookie-functions.js');
  require('../../app/assets/javascripts/consent.js');

});

afterAll(() => {

  require('./support/teardown.js');

});

describe("Cookie consent", () => {

  describe("hasConsentFor", () => {

    afterEach(() => {

      // remove cookie set by tests
      helpers.deleteCookie('cookies_policy');

    });

    test("If there is no consent cookie, return false", () => {

      expect(window.GOVUK.hasConsentFor('analytics')).toBe(false);

    });

    describe("If a consent cookie is set", () => {

      test("If the category is not saved in the cookie, return false", () => {

        window.GOVUK.setConsentCookie({ 'usage': true });

        expect(window.GOVUK.hasConsentFor('analytics')).toBe(false);

      });

      test("If the category is saved in the cookie, return its value", () => {

        window.GOVUK.setConsentCookie({ 'analytics': true });

        expect(window.GOVUK.hasConsentFor('analytics')).toBe(true);

      });

    });

  });

});
