import ErrorBanner from '../../app/assets/javascripts/esm/error-banner.mjs';
import { jest } from '@jest/globals';

describe("Error Banner", () => {

  beforeEach(() => {
    document.body.classList.add('govuk-frontend-supported');
  });

  afterEach(() => {
    document.body.innerHTML = '';
    jest.restoreAllMocks();
  });

  describe("The `hideBanner` method", () => {
    test("Will hide the element", () => {
      document.body.innerHTML = `
      <div class="govuk-error-summary" aria-labelledby="error-summary-title" role="alert" aria-live="polite" tabindex="-1" data-module="govuk-error-summary">
      </div>`;
      new ErrorBanner().hideBanner();
      expect(document.querySelector('.govuk-error-summary').hasAttribute('hidden')).toBe(true);
    });
  });

  describe("The `showBanner` method", () => {
    beforeEach(() => {
      document.body.innerHTML = `
      <div class="govuk-error-summary" aria-labelledby="error-summary-title" role="alert" aria-live="polite" tabindex="-1" data-module="govuk-error-summary">
      </div>`;

       new ErrorBanner().showBanner();
    });

    test("Will show the element", () => {
      expect(document.querySelector('.govuk-error-summary').hasAttribute('hidden')).toBe(false);
    });
  });

  describe("Passing a CSS selector to the module", () => {

    test("Will show the element", () => {
      document.body.innerHTML = `
      <div class="custom-css-class" hidden>
      </div>`;
      new ErrorBanner('.custom-css-class').showBanner();

      expect(document.querySelector('.custom-css-class').hasAttribute('hidden')).toBe(false);
    });

    test("Will hide the element", () => {
      document.body.innerHTML = `
      <div class="custom-css-class">
      </div>`;
      new ErrorBanner('.custom-css-class').hideBanner();

      expect(document.querySelector('.custom-css-class').hasAttribute('hidden')).toBe(true);
    });
  });
});
