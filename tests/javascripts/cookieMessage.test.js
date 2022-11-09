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
    cookieMessageStyles.textContent = '.notify-cookie-banner { display: none; }';
    document.getElementsByTagName('head')[0].appendChild(cookieMessageStyles);

    // protect against any previous tests setting a cookies-policy cookie
    helpers.deleteCookie('cookies-policy');

  });

  beforeEach(() => {

    // add the script GA looks for in the document
    document.body.appendChild(document.createElement('script'));

    jest.spyOn(window.GOVUK, 'initAnalytics');

    cookieMessage = `
      <div id="global-cookie-message" class="notify-cookie-banner" data-notify-module="cookie-banner" role="region" aria-label="cookie banner">
        <div class="notify-cookie-banner__wrapper govuk-width-container">
          <h2 class="notify-cookie-banner__heading govuk-heading-m" id="notify-cookie-banner__heading">Can we store analytics cookies on your device?</h2>
          <p class="govuk-body">Analytics cookies help us understand how our website is being used.</p>
          <div class="notify-cookie-banner__buttons">
            <button type="button" class="govuk-button notify-cookie-banner__button notify-cookie-banner__button-accept" type="button" data-accept-cookies="true" aria-describedby="notify-cookie-banner__heading">
              Yes<span class="govuk-visually-hidden">, Notify can store analytics cookies on your device</span>
            </button>
            <button type="button" class="govuk-button notify-cookie-banner__button notify-cookie-banner__button-reject" type="button" data-accept-cookies="false" aria-describedby="notify-cookie-banner__heading">
              No<span class="govuk-visually-hidden">, Notify cannot store analytics cookies on your device</span>
            </button>
            <a class="govuk-link notify-cookie-banner__link" href="/cookies">How Notify uses cookies</a>
          </div>
        </div>

        <div class="notify-cookie-banner__confirmation govuk-width-container" tabindex="-1">
          <p class="notify-cookie-banner__confirmation-message govuk-body">
            You can <a class="govuk-link" href="/cookies">change your cookie settings</a> at any time.
          </p>
          <button class="notify-cookie-banner__hide-button govuk-link" data-hide-cookie-banner="true" role="link">Hide<span class="govuk-visually-hidden"> cookies message</span></button>
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

    expect(helpers.element(document.querySelector('.notify-cookie-banner')).is('hidden')).toBe(true);

  });

  describe("If user hasn't made a choice to give their consent or not", () => {

    beforeEach(() => {

      window.GOVUK.notifyModules.start();

    });

    test("The cookie banner should show", () => {

      const banner = helpers.element(document.querySelector('.notify-cookie-banner'));

      expect(banner.is('hidden')).toBe(false);

    });

    test("No analytics should run", () => {

      expect(window.GOVUK.initAnalytics).not.toHaveBeenCalled();

    });

    describe("If the user clicks the button to accept analytics", () => {

      beforeEach(() => {

        const acceptButton = document.querySelector('.notify-cookie-banner__button-accept');

        helpers.triggerEvent(acceptButton, 'click');

      });

      test("the banner should confirm your choice and link to the cookies page as a way to change your mind", () => {

        confirmation = helpers.element(document.querySelector('.notify-cookie-banner__confirmation'));

        expect(confirmation.is('hidden')).toBe(false);
        expect(confirmation.el.textContent.trim()).toEqual(expect.stringMatching(/^You’ve accepted analytics cookies/));

      });

      test("If the user clicks the 'hide' button, the banner should be hidden", () => {

        const hideButton = document.querySelector('.notify-cookie-banner__hide-button');
        const banner = helpers.element(document.querySelector('.notify-cookie-banner'));

        helpers.triggerEvent(hideButton, 'click');

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

        const rejectButton = document.querySelector('.notify-cookie-banner__button-reject');

        helpers.triggerEvent(rejectButton, 'click');

      });

      test("the banner should confirm your choice and link to the cookies page as a way to change your mind", () => {

        confirmation = helpers.element(document.querySelector('.notify-cookie-banner__confirmation'));

        expect(confirmation.is('hidden')).toBe(false);
        expect(confirmation.el.textContent.trim()).toEqual(expect.stringMatching(/^You told us not to use analytics cookies/));

      });

      test("If the user clicks the 'hide' button, the banner should be hidden", () => {

        const hideButton = document.querySelector('.notify-cookie-banner__hide-button');
        const banner = helpers.element(document.querySelector('.notify-cookie-banner'));

        helpers.triggerEvent(hideButton, 'click');

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
