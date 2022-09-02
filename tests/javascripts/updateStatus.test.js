const each = require('jest-each').default;

const helpers = require('./support/helpers.js');

const serviceNumber = '6658542f-0cad-491f-bec8-ab8457700ead';
const updatesURL = `/services/${serviceNumber}/templates/count-sms-length`;

let responseObj = {};
let jqueryAJAXReturnObj;

beforeAll(() => {

  // ensure all timers go through Jest
  jest.useFakeTimers();

  // mock the bits of jQuery used
  jest.spyOn(window.$, 'ajax');

  // set up the object returned from $.ajax so it responds with whatever responseObj is set to
  jqueryAJAXReturnObj = {
    done: callback => {
      // For these tests the server responds immediately
      callback(responseObj);
      return jqueryAJAXReturnObj;
    },
    fail: () => {}
  };

  $.ajax.mockImplementation(() => jqueryAJAXReturnObj);

  require('../../app/assets/javascripts/updateStatus.js');

});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Update content', () => {

  beforeEach(() => {

    document.body.innerHTML = `
      <form>
        <input type="hidden" name="csrf_token" value="abc123" />
        <label for="template_content" id="template-content-label">Template content<label>
        <span id="example-hint-text">Example hint text</span>
        <textarea name="template_content" id="template_content" aria-describedby="example-hint-text">Content of message</textarea>
      </form>
      <div data-module="update-status" data-updates-url="${updatesURL}" data-target="template_content">
        Initial content
      </div>
    `;

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // tidy up record of mocked AJAX calls
    $.ajax.mockClear();

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

  });

  test("It should add attributes to the elements", () => {

    window.GOVUK.modules.start();

    expect(
      document.querySelectorAll('[data-module=update-status]')[0].id
    ).toEqual(
      "update-status"
    );

    expect(
      document.getElementById('template_content').getAttribute('aria-describedby')
    ).toEqual(
      "example-hint-text update-status"
    );

  });

  test("It should handle a textarea without an aria-describedby attribute", () => {

    document.getElementById('template_content').removeAttribute('aria-describedby');

    window.GOVUK.modules.start();

    expect(
      document.getElementById('template_content').getAttribute('aria-describedby')
    ).toEqual(
      "update-status"
    );

  });

  test("It should make requests to the URL specified in the data-updates-url attribute", () => {

    window.GOVUK.modules.start();

    expect($.ajax.mock.calls[0][0]).toEqual(updatesURL);
    expect($.ajax.mock.calls[0]).toEqual([
      updatesURL,
      {
        "data": "csrf_token=abc123&template_content=Content%20of%20message",
        "method": "post"
      }
    ]);

  });

  test("It should replace the content of the div with the returned HTML", () => {

    responseObj = {'html': 'Updated content'}

    expect(
      document.querySelectorAll('[data-module=update-status]')[0].textContent.trim()
    ).toEqual(
      "Initial content"
    );

    window.GOVUK.modules.start();

    expect(
      document.querySelectorAll('[data-module=update-status]')[0].textContent.trim()
    ).toEqual(
      "Updated content"
    );

  });

  test("It should fire when the content of the textarea changes", () => {

    let textarea = document.getElementById('template_content');

    // Initial update triggered
    window.GOVUK.modules.start();
    expect($.ajax.mock.calls.length).toEqual(1);

    // 150ms of inactivity
    jest.advanceTimersByTime(150);
    helpers.triggerEvent(textarea, 'input');

    expect($.ajax.mock.calls.length).toEqual(2);

  });

  test("It should fire only after 150ms of inactivity", () => {

    let textarea = document.getElementById('template_content');

    // Initial update triggered
    window.GOVUK.modules.start();
    expect($.ajax.mock.calls.length).toEqual(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect($.ajax.mock.calls.length).toEqual(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect($.ajax.mock.calls.length).toEqual(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect($.ajax.mock.calls.length).toEqual(1);

    // > 150ms of inactivity
    jest.advanceTimersByTime(1);
    expect($.ajax.mock.calls.length).toEqual(2);

  });

});
