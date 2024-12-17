import ErrorBanner from "../../app/assets/javascripts/esm/error-banner.mjs";

beforeAll(() => {
  // add class to mimic IRL 
  document.body.classList.add('govuk-frontend-supported')
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
      new ErrorBanner().hideBanner();
      expect(document.querySelector('.govuk-error-summary').classList).toContain('govuk-!-display-none')
    });
  });

  describe("The `showBanner` method", () => {
    beforeEach(() => {
      document.body.innerHTML = `
      <div class="govuk-error-summary" aria-labelledby="error-summary-title" role="alert" aria-live="polite" tabindex="-1" data-module="govuk-error-summary">
      </div>`;

      new ErrorBanner().showBanner('Some Err');
    });

    test("Will show the element", () => {
      expect(document.querySelector('.govuk-error-summary').classList).not.toContain('govuk-!-display-none')
    });
  });
});
