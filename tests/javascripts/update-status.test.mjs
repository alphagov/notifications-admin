import UpdateStatus from '../../app/assets/javascripts/esm/update-status.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers.js';

const serviceNumber = '6658542f-0cad-491f-bec8-ab8457700ead';
const updatesURL = `/services/${serviceNumber}/templates/count-sms-length`;


beforeAll(() => {

  // ensure all timers go through Jest
  jest.useFakeTimers();

});

describe('Update content', () => {

  let $module;
  let updateStatus;
  let mockFetch;

  beforeEach(() => {

    // Mock the window fetch function
    mockFetch = jest.fn();
    window.fetch = mockFetch;

    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <form>
        <input type="hidden" name="csrf_token" value="abc123" />
        <label for="template_content" id="template-content-label">Template content<label>
        <span id="example-hint-text">Example hint text</span>
        <textarea name="template_content" id="template_content" aria-describedby="example-hint-text">Content of message</textarea>
      </form>
      <div class="status-container" hidden>
        <div data-notify-module="update-status" data-updates-url="${updatesURL}" data-target="template_content">
          Initial content
        </div>
      </div>
    `;

    $module = document.querySelector('[data-notify-module="update-status"]')

    // Instantiate the class
    updateStatus = new UpdateStatus($module);

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

    jest.restoreAllMocks();

  });

  test("It should add attributes to the elements", () => {

    updateStatus.init();

    expect(
      document.querySelectorAll('[data-notify-module=update-status]')[0].id
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

    updateStatus.init();

    expect(
      document.getElementById('template_content').getAttribute('aria-describedby')
    ).toEqual(
      "update-status"
    );

  });

  test("It should make requests to the URL specified in the data-updates-url attribute", async () => {

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve()
    });

    await updateStatus.init();

    expect(mockFetch).toHaveBeenCalledWith(updatesURL, {
      method: 'POST',
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "csrf_token=abc123&template_content=Content+of+message",
    });

  });

  test("It should replace the content of the div with the returned HTML", async () => {

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({'html': 'Updated content'})
    });

    expect(
      document.querySelectorAll('[data-notify-module=update-status]')[0].textContent.trim()
    ).toEqual(
      "Initial content"
    );

    await updateStatus.update();

    expect(
      document.querySelectorAll('[data-notify-module=update-status]')[0].textContent.trim()
    ).toEqual(
      "Updated content"
    );

  });

  test("It should fire when the content of the textarea changes", () => {

    jest.spyOn(updateStatus, 'update');

    let textarea = document.getElementById('template_content');

    // Initial update triggered
    updateStatus.init();

    expect(updateStatus.update).toHaveBeenCalledTimes(1);

    // 150ms of inactivity
    jest.advanceTimersByTime(150);
    helpers.triggerEvent(textarea, 'input');

    expect(updateStatus.update).toHaveBeenCalledTimes(2);

  });

  test("It should fire only after 150ms of inactivity", () => {

    jest.spyOn(updateStatus, 'update');

    let textarea = document.getElementById('template_content');

    // Initial update triggered
    updateStatus.init();
    expect(updateStatus.update).toHaveBeenCalledTimes(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect(updateStatus.update).toHaveBeenCalledTimes(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect(updateStatus.update).toHaveBeenCalledTimes(1);

    helpers.triggerEvent(textarea, 'input');
    jest.advanceTimersByTime(149);
    expect(updateStatus.update).toHaveBeenCalledTimes(1);

    // > 150ms of inactivity
    jest.advanceTimersByTime(1);
    expect(updateStatus.update).toHaveBeenCalledTimes(2);

  });

  test('It should throw an error if the request fetch initiated fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Fetch error'));
    // Spy on console.error
    console.error = jest.fn();

    await updateStatus.update();

    expect(console.error).toHaveBeenCalledWith(
      'Failed to update status:',
      expect.any(Error)
    );
  });

  test("It should not call getRenderer if the response is not ok", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false
    });
    // spy on getRenderer
    jest.spyOn(updateStatus, 'getRenderer');

    await updateStatus.update();

    expect(updateStatus.getRenderer).not.toHaveBeenCalled();
  });

});
