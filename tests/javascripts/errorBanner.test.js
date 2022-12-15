beforeAll(() => {
  require('../../app/assets/javascripts/errorBanner.js')
});

afterAll(() => {
    require('./support/teardown.js');
});

describe("Error Banner", () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe("The `hideBanner` method", () => {
    test("Will hide the element", () => {
      document.body.innerHTML = `
      <div class="govuk-error-summary" aria-labelledby="error-summary-title" role="alert" aria-live="polite" tabindex="-1" data-module="govuk-error-summary">
      </div>`;
      window.GOVUK.ErrorBanner.hideBanner();
      expect(document.querySelector('.govuk-error-summary').classList).toContain('govuk-!-display-none')
    });
  });

  describe("The `showBanner` method", () => {
    beforeEach(() => {
      document.body.innerHTML = `
      <div class="govuk-error-summary" aria-labelledby="error-summary-title" role="alert" aria-live="polite" tabindex="-1" data-module="govuk-error-summary">
      </div>`;

      window.GOVUK.ErrorBanner.showBanner('Some Err');
    });

    test("Will show the element", () => {
      expect(document.querySelector('.govuk-error-summary').classList).not.toContain('govuk-!-display-none')
    });
  });
});
