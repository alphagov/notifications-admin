const helpers = require('./support/helpers');

beforeAll(() => {

  require('../../app/assets/javascripts/govuk/cookie-functions.js');
  require('../../app/assets/javascripts/analytics/analytics.js');
  require('../../app/assets/javascripts/analytics/init.js');
  require('../../app/assets/javascripts/cookieMessage.js');

});

afterAll(() => {

  require('./support/teardown.js');

});

describe("Cookie message", () => {

  let cookieMessage;

  beforeAll(() => {

    const cookieMessageStyles = document.createElement('style');

    // add the CSS that hides the cookie message by default
    document.getElementsByTagName('head')[0].appendChild(cookieMessageStyles);

    // protect against any previous tests setting a cookies-policy cookie
    helpers.deleteCookie('cookies-policy');

  });

  beforeEach(() => {

    // add the script GA looks for in the document
    document.body.appendChild(document.createElement('script'));

    jest.spyOn(window.GOVUK, 'initAnalytics');

    cookieMessage = `
    <div id="global-cookie-message" class="govuk-cookie-banner" data-notify-module="cookie-banner" data-nosnippet role="region" aria-label="Cookies on GOV.UK Notify" hidden>
    <div class="govuk-cookie-banner__message js-cookie-banner-message govuk-width-container">
      <div class="govuk-grid-row">
        <div class="govuk-grid-column-two-thirds">
          <h2 class="govuk-cookie-banner__heading govuk-heading-m">
            Can we store analytics cookies on your device?
          </h2>
          <div class="govuk-cookie-banner__content">
            <p class="govuk-body">Analytics cookies help us understand how our website is being used.</p>
          </div>
        </div>
      </div>
      <div class="govuk-button-group">
        <button type="button" class="govuk-button" data-module="govuk-button" data-accept-cookies="true">
          Accept analytics cookies
        </button>
        <button type="button" class="govuk-button" data-module="govuk-button" data-accept-cookies="false">
          Reject analytics cookies
        </button>
        <a class="govuk-link" href="/cookies">How Notify uses cookies</a>
      </div>
    </div>
    <div class="govuk-cookie-banner__message govuk-width-container" hidden>
      <div class="govuk-grid-row">
        <div class="govuk-grid-column-two-thirds">
          <div class="govuk-cookie-banner__content">
            <p class="govuk-body govuk-cookie-banner__confirmation-message">You can <a class="govuk-link" href="/cookies">change your cookie settings</a> at any time.</p>
          </div>
        </div>
      </div>
      <div class="govuk-button-group">
        <button value="yes" type="submit" name="cookies[hide]" class="govuk-button" data-module="govuk-button">
          Hide cookie message
        </button>
      </div>
    </div>
    <div class="govuk-cookie-banner__message js-cookie-banner__accept-message govuk-width-container" role="alert" hidden>
      <div class="govuk-grid-row">
        <div class="govuk-grid-column-two-thirds">
          <div class="govuk-cookie-banner__content">
            <p class="govuk-body">You’ve accepted analytics cookies. You can <a class="govuk-link" href="/cookies">change your cookie settings</a> at any time.</p>
          </div>
        </div>
      </div>
      <div class="govuk-button-group">
        <button value="yes" type="submit" name="cookies[hide]" class="govuk-button" data-module="govuk-button" data-hide-cookie-banner="true">
          Hide cookie message
        </button>
      </div>
    </div>
    <div class="govuk-cookie-banner__message js-cookie-banner__reject-message govuk-width-container" role="alert" hidden>
      <div class="govuk-grid-row">
        <div class="govuk-grid-column-two-thirds">
          <div class="govuk-cookie-banner__content">
            <p class="govuk-body">You told us not to use analytics cookies. You can <a class="govuk-link" href="/cookies">change your cookie settings</a> at any time.</p>
          </div>
        </div>
      </div>
      <div class="govuk-button-group">
      <button value="yes" type="submit" name="cookies[hide]" class="govuk-button" data-module="govuk-button" data-hide-cookie-banner="true">
        Hide cookie message
      </button>
      </div>
    </div>
  </div>`;

    document.body.innerHTML += cookieMessage;

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // remove cookie set by tests
    helpers.deleteCookie('cookies_policy');

    // reset spies
    window.GOVUK.initAnalytics.mockClear();

    // remove analytics tracker
    delete window.GOVUK.analytics;

    // reset global variable to state when init.js loaded
    window['ga-disable-UA-26179049-1'] = true;

  });

  /*
    Note: If no JS, the cookie banner is hidden.

    This works through CSS, based on the presence of the `js-enabled` class on the <body> so is not tested here.
  */

  describe("The `clearOldCookies` method", () => {

    test("Will clear the seen_cookie_message cookie if it still exists", () => {

      // seen_cookie_message was set on the www domain, which setCookie defaults to
      helpers.setCookie('seen_cookie_message', 'true', { 'days': 365 });

      window.GOVUK.NotifyModules.CookieBanner.clearOldCookies({ "analytics": false });

      expect(window.GOVUK.cookie('seen_cookie_message')).toBeNull();

    });

    test("Will clear any existing Google Analytics cookies if consent is not set", () => {

      // GA cookies are set on the root domain
      helpers.setCookie('_ga', 'GA1.1.123.123', { 'days': 365, 'domain': '.notifications.service.gov.uk' });
      helpers.setCookie('_gid', 'GA1.1.456.456', { 'days': 1, 'domain': '.notifications.service.gov.uk' });

      window.GOVUK.NotifyModules.CookieBanner.clearOldCookies(null);

      expect(window.GOVUK.cookie('_ga')).toBeNull();
      expect(window.GOVUK.cookie('_gid')).toBeNull();

    });

    test("Will leave any existing Google Analytics cookies if consent is set", () => {

      helpers.setCookie('_ga', 'GA1.1.123.123', { 'days': 365 });
      helpers.setCookie('_gid', 'GA1.1.456.456', { 'days': 1 });

      window.GOVUK.NotifyModules.CookieBanner.clearOldCookies({ "analytics": true });

      expect(window.GOVUK.cookie('_ga')).not.toBeNull();
      expect(window.GOVUK.cookie('_gid')).not.toBeNull();

    });

  });

  test("If user has made a choice to give their consent or not, the cookie banner should be hidden", () => {

    window.GOVUK.setConsentCookie({ 'analytics': false });

    window.GOVUK.notifyModules.start()

    expect(helpers.element(document.querySelector('.govuk-cookie-banner')).is('hidden')).toBe(true);

  });

  describe("If user hasn't made a choice to give their consent or not", () => {

    beforeEach(() => {

      window.GOVUK.notifyModules.start();

    });

    test("The cookie banner should show", () => {

      const banner = helpers.element(document.querySelector('.govuk-cookie-banner'));

      expect(banner.is('hidden')).toBe(false);

    });

    test("No analytics should run", () => {

      expect(window.GOVUK.initAnalytics).not.toHaveBeenCalled();

    });

    describe("If the user clicks the button to accept analytics", () => {

      beforeEach(() => {

        const acceptButton = document.querySelector('button[data-accept-cookies=true]');

        helpers.triggerEvent(acceptButton, 'click');

      });

      test("the banner should confirm your choice and link to the cookies page as a way to change your mind", () => {

        confirmation = helpers.element(document.querySelector('.js-cookie-banner__accept-message'));

        expect(confirmation.is('hidden')).toBe(false);
        expect(confirmation.el.textContent.trim()).toEqual(expect.stringMatching(/^You’ve accepted analytics cookies/));

      });

      test("If the user clicks the 'hide' button, the banner should be hidden", () => {

        const hideButton = document.querySelectorAll('button[data-hide-cookie-banner=true]');
        const banner = helpers.element(document.querySelector('.govuk-cookie-banner'));

        helpers.triggerEvent(hideButton[0], 'click');

        expect(banner.is('hidden')).toBe(true);

      });

      test("The consent cookie should be set, with analytics set to 'true'", () => {

        expect(window.GOVUK.getConsentCookie()).toEqual({ 'analytics': true });

      });

      test("The analytics should be set up", () => {

        expect(window.GOVUK.analytics).toBeDefined();

      });

    });

    describe("If the user clicks the button to reject analytics", () => {

      beforeEach(() => {

        const rejectButton = document.querySelector('button[data-accept-cookies=false]');

        helpers.triggerEvent(rejectButton, 'click');

      });

      test("the banner should confirm your choice and link to the cookies page as a way to change your mind", () => {

        confirmation = helpers.element(document.querySelector('.js-cookie-banner__reject-message .govuk-cookie-banner__content'));

        expect(confirmation.is('hidden')).toBe(false);
        expect(confirmation.el.textContent.trim()).toEqual(expect.stringMatching(/^You told us not to use analytics cookies/));

      });

      test("If the user clicks the 'hide' button, the banner should be hidden", () => {

        const hideButton = document.querySelectorAll('button[data-hide-cookie-banner=true]');
        const banner = helpers.element(document.querySelector('.govuk-cookie-banner'));

        helpers.triggerEvent(hideButton[1], 'click');

        expect(banner.is('hidden')).toBe(true);

      });

      test("The consent cookie should be set, with analytics set to 'false'", () => {

        expect(window.GOVUK.getConsentCookie()).toEqual({ 'analytics': false });

      });

      test("The analytics should not be set up", () => {

        expect(window.GOVUK.analytics).not.toBeDefined();

      });

    });

  });

});
