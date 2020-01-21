beforeAll(() => {
  require('../../app/assets/javascripts/errorTracking.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Error tracking', () => {

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `<div data-module="track-error" data-error-type="validation" data-error-label="missing field"></div>`;

  });

  afterEach(() => {

    document.body.innerHTML = '';
    delete window.GOVUK.analytics;

  });

  test("If there is an analytics tracker set up, it should send details of the error to window.GOVUK.analytic", () => {

    window.GOVUK.analytics = {
      'trackEvent': jest.fn()
    };

    // start the module
    window.GOVUK.modules.start();

    expect(window.GOVUK.analytics.trackEvent).toHaveBeenCalled();
    expect(window.GOVUK.analytics.trackEvent.mock.calls[0]).toEqual(['Error', 'validation', {
      'label': 'missing field'
    }]);

  });

});
