const helpers = require('./support/helpers.js');

beforeAll(() => {
  jest.useFakeTimers();
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Prevent duplicate form submissions', () => {

  let form;
  let button;
  let consoleErrorSpy;

  beforeAll(() => {

    // spy on console.error to track JSDOM errors
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

  });

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <form action="/" method="post">
        <button class="govuk-button" type="submit">Continue</button>
      </form>`;

    form = document.querySelector('form');
    button = document.querySelector('button');

    // reset all tracking of calls to console.error
    consoleErrorSpy.mockClear();

    require('../../app/assets/javascripts/preventDuplicateFormSubmissions.js');

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // we run the preventDuplicateFormSubmissions.js script every test
    // the module cache needs resetting each time for the script to execute
    jest.resetModules();

  });

  afterAll(() => {

    consoleErrorSpy.mockRestore();

  });

  test("It should prevent any clicks of the 'submit' button after the first one submitting the form", () => {

    helpers.triggerEvent(button, 'click');
    helpers.triggerEvent(button, 'click');

    // JSDOM doesn't implement form submissions
    // see https://github.com/jsdom/jsdom/issues/1937#issuecomment-321575590
    //
    // If a form submission is caused by a input/button[type=submit], this instead outputs a
    // 'not implemented' error from the requestSubmit method.
    //
    // That means we can assume any errors of that type would be the same as a form submission in
    // browsers.
    expect(consoleErrorSpy.mock.calls.length).toEqual(1);
    expect(consoleErrorSpy.mock.calls[0][0].message).toEqual('Not implemented: HTMLFormElement.prototype.requestSubmit')

  });

  test("It should allow clicks again after 1.5 seconds", () => {

    helpers.triggerEvent(button, 'click');

    jest.advanceTimersByTime(1500);

    helpers.triggerEvent(button, 'click');

    // JSDOM doesn't implement form submissions
    // see https://github.com/jsdom/jsdom/issues/1937#issuecomment-321575590
    //
    // If a form submission is caused by a input/button[type=submit], this instead outputs a
    // 'not implemented' error from the requestSubmit method.
    //
    // That means we can assume any errors of that type would be the same as a form submission in
    // browsers.
    expect(consoleErrorSpy.mock.calls.length).toEqual(2);
    expect(consoleErrorSpy.mock.calls[0][0].message).toEqual('Not implemented: HTMLFormElement.prototype.requestSubmit')
    expect(consoleErrorSpy.mock.calls[1][0].message).toEqual('Not implemented: HTMLFormElement.prototype.requestSubmit')

  });

});
