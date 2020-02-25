const helpers = require('./support/helpers');

beforeAll(() => {

  require('../../app/assets/javascripts/govuk/cookie-functions.js');
  require('../../app/assets/javascripts/consent.js');
  require('../../app/assets/javascripts/analytics/analytics.js');
  require('../../app/assets/javascripts/analytics/init.js');
  require('../../app/assets/javascripts/cookieSettings.js');

});

afterAll(() => {

  require('./support/teardown.js');

});

describe("Cookie settings", () => {

  let cookiesPageContent;
  let yesRadio;
  let noRadio;
  let saveButton;

  beforeEach(() => {

    // add the script GA looks for in the document
    document.body.appendChild(document.createElement('script'));

    window.ga = jest.fn();
    jest.spyOn(window.GOVUK, 'initAnalytics');

    cookiesPageContent = `
      <div class="cookie-settings__confirmation banner banner-with-tick" data-cookie-confirmation="true" role="group" tabindex="-1">
        <h2 class="banner-title">Your cookie settings were saved</h2>
        <a class="govuk_link govuk_link--no-visited-state cookie-settings__prev-page" href="#" data-module="track-click" data-track-category="cookieSettings" data-track-action="Back to previous page">
          Go back to the page you were looking at
        </a>
      </div>
      <h1 class="heading-large">Cookies</h1>
      <p class="summary">
          Cookies are small files saved on your phone, tablet or computer when you visit a website.
      </p>
      <p>We use cookies to make GOV.UK Notify work and collect information about how you use our service.</p>
      <div class="cookie-settings__no-js">
        <h2 class="govuk-heading-s govuk-!-margin-top-6">Do you want to accept analytics cookies?</h2>
        <p>We use Javascript to set most of our cookies. Unfortunately Javascript is not running on your browser, so you cannot change your settings. You can try:</p>
        <ul class="govuk-list govuk-list--bullet">
          <li>reloading the page</li>
          <li>turning on Javascript in your browser</li>
        </ul>
      </div>
      <h2 class="heading-medium">Analytics cookies (optional)</h2>
      <div class="cookie-settings__form-wrapper">
        <form data-module="cookie-settings">
          <div class="govuk-form-group govuk-!-margin-top-6">
            <fieldset class="govuk-fieldset" aria-describedby="changed-name-hint">
              <legend class="govuk-fieldset__legend govuk-fieldset__legend--s">
                Do you want to accept analytics cookies?
              </legend>
              <div class="govuk-radios govuk-radios--inline">
                <div class="govuk-radios__item">
                  <input class="govuk-radios__input" id="cookies-analytics-yes" name="cookies-analytics" type="radio" value="on">
                  <label class="govuk-label govuk-radios__label" for="cookies-analytics-yes">
                    Yes
                  </label>
                </div>
                <div class="govuk-radios__item">
                  <input class="govuk-radios__input" id="cookies-analytics-no" name="cookies-analytics" type="radio" value="off">
                  <label class="govuk-label govuk-radios__label" for="cookies-analytics-no">
                    No
                  </label>
                </div>
              </div>
            </fieldset>
          </div>
          <button class="govuk-button" type="submit">Save cookie settings</button>
        </form>
      </div>`;

    document.body.innerHTML += cookiesPageContent;

    yesRadio = document.querySelector('#cookies-analytics-yes');
    noRadio = document.querySelector('#cookies-analytics-no');
    saveButton = document.querySelector('.govuk-button');

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // remove cookie set by tests
    helpers.deleteCookie('cookies_policy');

    // reset spies
    window.ga.mockClear();
    window.GOVUK.initAnalytics.mockClear();

    // remove analytics tracker
    delete window.GOVUK.analytics;

    // reset global variable to state when init.js loaded
    window['ga-disable-UA-26179049-1'] = true;

  });

  /* 
    Note: If no JS, the cookies page contains content to explain why JS is required to set analytics cookies.
          This is hidden if JS is available when the page loads.

          The message displayed to confirm any selection made is also in the page but hidden on load.

    Both of these work through CSS, based on the presence of the `js-enabled` class on the <body> so are not tested here.
  */

  describe("When the page loads", () => {

    test("If user has not chosen to accept or reject analytics, the radios for making that choice should be set to unchecked", () => {

      window.GOVUK.modules.start();

      expect(yesRadio.checked).toBe(false);
      expect(noRadio.checked).toBe(false);

    });

    test("If analytics are accepted, the radio for 'accept analytics' should be set to checked", () => {

      window.GOVUK.setConsentCookie({ 'analytics': true });

      window.GOVUK.modules.start();

      expect(yesRadio.checked).toBe(true);
      expect(noRadio.checked).toBe(false);

    });

    test("If analytics are rejected, the radio for 'reject analytics' should be set to checked", () => {

      window.GOVUK.setConsentCookie({ 'analytics': false });

      window.GOVUK.modules.start();

      expect(yesRadio.checked).toBe(false);
      expect(noRadio.checked).toBe(true);

    });

  });

  describe("When the 'Save cookie settings' button is clicked", () => {

    beforeEach(() => {

      window.GOVUK.modules.start();

    });

    test("If no selection is made, set consent to reject analytics", () => {

      helpers.triggerEvent(saveButton, 'click');

      expect(window.GOVUK.getConsentCookie()).toEqual({ 'analytics': false });

    });

    test("If a selection is made, save this as consent", () => {

      yesRadio.checked = true;

      helpers.triggerEvent(saveButton, 'click');

      expect(window.GOVUK.getConsentCookie()).toEqual({ 'analytics': true });

    });

    describe("The message confirming your choice", () => {

      let confirmationMessage;

      beforeEach(() => {

        confirmationMessage = document.querySelector('.cookie-settings__confirmation');
        helpers.triggerEvent(saveButton, 'click');

      });

      test("Should be shown when the 'Save cookie settings' button is clicked", () => {

        expect(helpers.element(confirmationMessage).is('hidden')).toBe(false);

      });

      test("Should include a link to the last page visited, if information on the referrer is available", () => {

        jest.spyOn(document, 'referrer', 'get').mockReturnValue('https://notifications.service.gov.uk/privacy');

        helpers.triggerEvent(saveButton, 'click');

        expect(confirmationMessage.querySelector('.cookie-settings__prev-page').getAttribute('href')).toEqual('/privacy');

      });

    });

    describe("Analytics code", () => {

      beforeAll(() => {

        jest.spyOn(window, 'location', 'get').mockImplementation(() => {

          return {
            'pathname': '/privacy',
            'search': ''
          }

        });

      });

      test("if user accepted analytics, the analytics code should initialise and register a pageview", () => {

        window.GOVUK.modules.start();

        yesRadio.checked = true;

        helpers.triggerEvent(saveButton, 'click');

        expect(window.GOVUK.initAnalytics).toHaveBeenCalled();

        expect(window.ga).toHaveBeenCalled();
        // the first 5 calls are configuration
        expect(window.ga.mock.calls[5]).toEqual(['send', 'pageview', '/privacy']);

      });

      test("if user rejected analytics, the analytics code should not run", () => {

        window.GOVUK.modules.start();

        noRadio.checked = true;

        helpers.triggerEvent(saveButton, 'click');

        expect(window.GOVUK.initAnalytics).not.toHaveBeenCalled();

      });

    });

  });

});
