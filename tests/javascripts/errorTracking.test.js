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

  });

  test("It should send the right data to Google Analytics", () => {

    window.ga = jest.fn(() => {});

    // start the module
    window.GOVUK.modules.start();

    expect(window.ga).toHaveBeenCalled();
    expect(window.ga.mock.calls[0]).toEqual(['send', 'event', 'Error', 'validation', 'missing field']);

  });

});
