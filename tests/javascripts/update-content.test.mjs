import UpdateContent from '../../app/assets/javascripts/esm/update-content.mjs';
import * as helpers from './support/helpers.js';
import { jest } from '@jest/globals';
import each from 'jest-each';

describe('Update content', () => {

  const serviceNumber = '6658542f-0cad-491f-bec8-ab8457700ead';
  const resourceURL = `/services/${serviceNumber}/notifications/email.json?status=sending%2Cdelivered%2Cfailed`;
  const updateKey = 'counts';

  let serverResponseData = {};
  let mockFetch;

  // helper to create a mocked response object for Fetch
  const createMockResponse = (data, status = 200, statusText = 'OK') => {
    return {
      ok: status >= 200 && status < 300,
      status: status,
      statusText: statusText,
      json: () => Promise.resolve(data),
    };
  };

  beforeAll(() => {

    // ensure all timers go through Jest
    jest.useFakeTimers();

    // mock Fetch API
    mockFetch = jest.fn();
    window.fetch = mockFetch;

  });

  afterAll(() => {
    jest.useRealTimers();
  });

  beforeEach(() => {
    document.body.classList.add('govuk-frontend-supported');
    mockFetch.mockImplementation(() => Promise.resolve(
      createMockResponse(serverResponseData)
    ));
  });

  afterEach(() => {
    document.body.innerHTML = '';

    // tidy up record of mocked Fetch calls
    mockFetch.mockClear();

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

  });

  const getInitialHTMLString = partial => `
    <div data-notify-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}">
      ${partial}
    </div>`;

  describe("All variations", () => {

    beforeEach(() => {
      // Intentionally basic example because we're not testing changes to the partial
      document.body.innerHTML = getInitialHTMLString(`<p class="notification-status">Sending</p>`);

      // default the response to match the content inside div[data-notify-module]
      serverResponseData[updateKey] = `<p class="notification-status">Sending</p>`;
    });

    describe("By default", () => {

      beforeEach(() => {
        new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));
      });

      test("It should use the GET HTTP method", async() => {
        
        await jest.advanceTimersByTimeAsync(2000);
        const mockFetchArguments = mockFetch.mock.calls[0];
        expect(mockFetchArguments[1].method).toEqual('GET');
      });

      test("It shouldn't send any data as part of the requests", async() => {

        await jest.advanceTimersByTimeAsync(2000);
        const mockFetchArguments = mockFetch.mock.calls[0];
        expect(mockFetchArguments[1].body).toBeUndefined();

      });

      test("It should request updates with a dynamic interval", async() => {

        // helper function to simulate the server taking time to respond
        const mockResponseDelay = async (delay) => {
          const mockResponse = createMockResponse(serverResponseData);
          
          await jest.advanceTimersByTimeAsync(delay);
          return mockResponse;
        };

        // override the default mockFetch implementation here
        // where first response is immediate but 2nd and 3rd take 1000ms
        mockFetch.mockImplementationOnce(() => Promise.resolve(
            createMockResponse(serverResponseData)
        ));
        mockFetch.mockImplementationOnce(() => mockResponseDelay(1000));
        mockFetch.mockImplementationOnce(() => mockResponseDelay(1000));

        await jest.advanceTimersByTimeAsync(1999);
        // Time from start of module: 1999ms
        // First call doesn’t happen in the first 1999ms
        expect(mockFetch).toHaveBeenCalledTimes(0);

        // Advance to time of first response (2000ms default timeout + 0ms response = 2000ms)
        await jest.advanceTimersByTimeAsync(1);
        expect(mockFetch).toHaveBeenCalledTimes(1);
        // Next request scheduled for: 2000ms + 1000ms backoff = 3000ms

        // Advance to time of second request (3000ms)
        await jest.advanceTimersByTimeAsync(1000);
        expect(mockFetch).toHaveBeenCalledTimes(2);

        // Advance to time of second response (3000ms + 1000ms = 4000ms)
        await jest.advanceTimersByTimeAsync(1000);
        // Next request scheduled for: 4000ms + 6905ms (delay2) = 10905ms

        // Time from start of module: 10904ms
        // Third call happens after a 6905ms polling interval, which is based on a response time of 1000ms
        // so shouldn't have happened by 6904ms
        await jest.advanceTimersByTimeAsync(5904);
        expect(mockFetch).toHaveBeenCalledTimes(2);

        // Time from start of module: 10905ms
        // But it should happen at 6905ms
        await jest.advanceTimersByTimeAsync(1);
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      test.each([
        [1000, 0],
        [1500, 100],
        [4590, 500],
        [6905, 1000],
        [24000, 10000],
      ])('It calculates a delay of %dms if the API responds in %dms', (waitTime, responseTime) => {
          expect(
            UpdateContent.prototype.calculateBackoff(responseTime)
          ).toBe(
            waitTime
          );
      });

    });

    describe("If a form is used as a source for data, referenced in the data-form attribute", () => {

      beforeEach(() => {
        // Add a form to the page
        document.body.innerHTML += `
          <form method="post" id="service">
            <input type="hidden" name="serviceName" value="Buckhurst surgery" />
            <input type="hidden" name="serviceNumber" value="${serviceNumber}" />
          </form>`;

        // Link the component to the form
        document.querySelector('[data-notify-module=update-content]').setAttribute('data-form', 'service');
  
        // start the module
        new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      });

      test("requests should use the same HTTP method as the form", async () => {
  
        await jest.advanceTimersByTimeAsync(2000)
        const mockFetchArguments = mockFetch.mock.calls[0];
        expect(mockFetchArguments[1].method).toEqual('POST');
      })

      test("requests should use the data from the form", async() => {

        await jest.advanceTimersByTimeAsync(2000)
        const fetchBody = mockFetch.mock.calls[0][1].body
        expect(fetchBody).toBe('serviceName=Buckhurst+surgery&serviceNumber=6658542f-0cad-491f-bec8-ab8457700ead');
        // we're using new URLSearchParams and new FormData where space is encoded as '+'
        // we no longer need getFormDataFromPairs helper
      })

    });

    test('With a 401 response status code, polling should be stopped', async() => {

      const locationMock = new helpers.LocationMock();

      window.location.reload = jest.fn();

      // Simulate server responding 1000ms after request is made with a 401
      const mockResponseDelay = async (delay) => {
        const mockResponse = createMockResponse({}, 401, 'Unauthorized');
        // simulate the server taking time to respond
        await jest.advanceTimersByTimeAsync(delay);
        return mockResponse;
      };
      mockFetch.mockImplementationOnce(() => mockResponseDelay(1000));
      
      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      expect(mockFetch).toHaveBeenCalledTimes(0);

      // Time from start of module: 2000ms
      // First call from polling happens at 2000ms
      await jest.advanceTimersByTimeAsync(2000);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Time from start of module: 3000ms
      await jest.advanceTimersByTimeAsync(1000);

      // We expect the 401 to trigger a page reload, to force a redirect to the sign in page
      expect(window.location.reload).toHaveBeenCalled();

      // Tidy up
      locationMock.reset();

    });

    test('With response.stop === 1, polling should be stopped', async() => {

      // Simulate server responding 1000ms after request is made with the stop flag set in its payload
      const responseWithStop = { stop: 1, ...serverResponseData };
      mockFetch.mockResolvedValueOnce(createMockResponse(responseWithStop));

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      expect(mockFetch).toHaveBeenCalledTimes(0);

      // Time from start of module: 2000ms
      // First call from polling happens at 2000ms
      await jest.advanceTimersByTimeAsync(2000);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Time from start of module: 4000ms
      await jest.advanceTimersByTimeAsync(2000);

      // We expect all future requests to be blocked by the last one having the stop flag set
      expect(mockFetch).toHaveBeenCalledTimes(1);

      delete responseWithStop.stop;
    });

  });

  describe('When updating the contents of DOM nodes', () => {

    let partialData;

    const getPartial = items => {
      let pillsHTML = '';

      items.forEach(item => {
        pillsHTML += `
          <li ${item.selected ? 'aria-selected="true"' : ''} role="tab">
            <div ${item.selected ? 'class="pill-selected-item" tabindex="0"' : ''}>
              <div class="big-number-smaller">
                <div class="big-number-number">${item.count}</div>
              </div>
              <div class="pill-label">${item.label}</div>
            </div>
          </li>`;
      });

      return `
        <div class="bottom-gutter ajax-block-container">
          <ul role="tablist" class="pill">
            ${pillsHTML}
          </ul>
        </div>`;
    };

    beforeEach(() => {

      partialData = [
        {
          count: 0,
          label: 'total',
          selected: true
        },
        {
          count: 0,
          label: 'sending',
          selected: false
        },
        {
          count: 0,
          label: 'delivered',
          selected: false
        },
        {
          count: 0,
          label: 'failed',
          selected: false
        }
      ];

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

    });

    test("It should replace the original HTML with that of the partial, to match that returned from fetch responses", async() => {

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      expect(document.querySelector('.ajax-block-container').parentNode.hasAttribute('data-resource')).toBe(false);

    });

    test("It should make requests to the URL specified in the data-resource attribute", async() => {

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      await jest.advanceTimersByTimeAsync(2000);

      expect(mockFetch.mock.calls[0][0]).toEqual(resourceURL);

    });

    test("If the response contains no changes, the DOM should stay the same and no update event should fire", async() => {

      // send the done callback a response with updates included
      serverResponseData[updateKey] = getPartial(partialData);

      const updateEventCallbackSpy = jest.fn();

      document.addEventListener("updateContent.onafterupdate", updateEventCallbackSpy);

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      // move to the time the first request is fired
       await jest.advanceTimersByTimeAsync(2000);

      // check a sample DOM node is unchanged
      expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("0");
      expect(updateEventCallbackSpy).not.toHaveBeenCalled()
    });

    test("If the response contains changes, it should update the DOM with them and fire an update event", async() => {

      const updateEventCallbackSpy = jest.fn();
      document.addEventListener("updateContent.onafterupdate", updateEventCallbackSpy);

      partialData[0].count = 1;

      // send the done callback a response with updates included
      serverResponseData[updateKey] = getPartial(partialData);

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      // move to the time the first request is fired
      await jest.advanceTimersByTimeAsync(2000);

      // check the right DOM node is updated
      expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("1");
      // check the event was triggered with the updated DOM node (the 2nd argument, after the event object)
      expect(updateEventCallbackSpy).toHaveBeenCalled();
      expect(updateEventCallbackSpy.mock.calls[0][0].detail.el[0]).toEqual(document.querySelector('.ajax-block-container'));

      // clean up the listener
      document.removeEventListener("updateContent.onafterupdate", updateEventCallbackSpy);
    });

  });

  describe("When adding or removing DOM nodes", () => {

    let partialData;

    const getPartial = items => {

      const getItemHTMLString = content => {
        var areas = '';

        content.areas.forEach(area =>
          areas += "\n" + `<li class="area-list-item area-list-item--unremoveable area-list-item--smaller">${area}</li>`
        );

        return `
          <div class="keyline-block">
            <div class="file-list govuk-!-margin-bottom-2">
              <h2>
                <a class="file-list-filename-large govuk-link govuk-link--no-visited-state" href="/services/7597847f-ad8e-4600-8faf-c42a647d8dee/current-alerts/b9e53cda-54f9-47bc-9fb2-b78a11eda6a9">${content.title}</a>
              </h2>
              <div class="govuk-grid-row">
                <div class="govuk-grid-column-one-half">
                  <span class="file-list-hint-large govuk-!-margin-bottom-2">
                    ${content.hint}
                  </span>
                </div>
                <div class="govuk-grid-column-one-half file-list-status">
                  <p class="govuk-body govuk-!-margin-bottom-0 govuk-hint">
                    ${content.status}
                  </p>
                </div>
              </div>
              <ul class="area-list">
                ${areas}
              </ul>
            </div>
          </div>`;
      };

      var itemsHTMLString = '';

      items.forEach(item => itemsHTMLString += "\n" + getItemHTMLString(item));

      return `<div class="ajax-block-container">
                ${itemsHTMLString};
                <div class="keyline-block"></div>
              </div>`;

    };

    beforeEach(() => {

      partialData = [
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        }
      ];

    });

    test("If the response contains no changes, the DOM should stay the same", async() => {

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

      // make a response with no changes
      serverResponseData[updateKey] = getPartial(partialData);

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      // move to the time the first request is fired
      await jest.advanceTimersByTimeAsync(2000);

      // check it has the same number of items
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

    test("If the response adds a node, the DOM should contain that node", async() => {

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

      partialData.push({
        title: "Reservoir flooding template",
        hint: "The local reservoir has flooded. All people within 5 miles should move to a safer location.",
        status: "Waiting for approval",
        areas: [
          "Santa Claus Village, Rovaniemi A",
          "Santa Claus Village, Rovaniemi D"
        ]
      });

      // make the response have an extra item
      serverResponseData[updateKey] = getPartial(partialData);

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      // move to the time the first request is fired
      await jest.advanceTimersByTimeAsync(2000);

      // check the node has been added
      expect(document.querySelectorAll('.file-list').length).toEqual(2);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");
      expect(document.querySelectorAll('.file-list h2 a')[1].textContent.trim()).toEqual("Reservoir flooding template");

    });

    test("If the response removes a node, the DOM should not contain that node", async() => {

      // add another item so we start with 2
      partialData.push({
        title: "Reservoir flooding template",
        hint: "The local reservoir has flooded. All people within 5 miles should move to a safer location.",
        status: "Waiting for approval",
        areas: [
          "Santa Claus Village, Rovaniemi A",
          "Santa Claus Village, Rovaniemi D"
        ]
      });

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

      // remove the last item
      partialData.pop();

      // default the response to match the content inside div[data-notify-module]
      serverResponseData[updateKey] = getPartial(partialData);

      // start the module
      new UpdateContent(document.querySelector('[data-notify-module="update-content"]'));

      // move to the time the first request is fired
      await jest.advanceTimersByTimeAsync(2000);

      // check the node has been removed
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

  });

});
