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
      <span class="govuk-error-message banner-dangerous js-error-visible">
      </span>`;
      window.GOVUK.ErrorBanner.hideBanner();
      expect(document.querySelector('.banner-dangerous').classList).toContain('govuk-!-display-none')
    });
  });

  describe("The `showBanner` method", () => {
    beforeEach(() => {
      document.body.innerHTML = `
        <span class="govuk-error-message banner-dangerous js-error-visible govuk-!-display-none">
        </span>`;

      window.GOVUK.ErrorBanner.showBanner('Some Err');
    });

    test("Will set a specific error message on the element", () => {
      expect(document.querySelector('.banner-dangerous').textContent).toEqual('Error: Some Err')
    });

    test("Will show the element", () => {
      expect(document.querySelector('.banner-dangerous').classList).not.toContain('govuk-!-display-none')
    });
  });
});
