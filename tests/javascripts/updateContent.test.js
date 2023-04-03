const each = require('jest-each').default;

const helpers = require('./support/helpers.js');

const serviceNumber = '6658542f-0cad-491f-bec8-ab8457700ead';
const resourceURL = `/services/${serviceNumber}/notifications/email.json?status=sending%2Cdelivered%2Cfailed`;
const updateKey = 'counts';

let responseObj = {};
let serverResponse;
let jqueryAJAXReturnObj;

beforeAll(() => {

  // ensure all timers go through Jest
  jest.useFakeTimers();

  // mock the bits of jQuery used
  jest.spyOn(window.$, 'ajax');

  // make the server response global so tests can change it
  serverResponse = {
    responseTimeInMilliseconds: 1000,
    statusCode: 200,
    complete: () => {
      responseObj.status = serverResponse.statusCode
      if (serverResponse.statusCode >= 300) {
        jqueryAJAXReturnObj.callbacks.fail(responseObj);
      } else {
        jqueryAJAXReturnObj.callbacks.done(responseObj);
      }
    }
  };

  // Each request made blocks any further ones for that resource until it completes so force a completion to unblock future tests
  forceRequestCompletion = () => {

    // Successful requests change the DOM and the interval used by all future requests so use a failing one instead
    serverResponse.statusCode = 500;
    serverResponse.complete()
    serverResponse.statusCode = 200;

  };

  // set up the object returned from $.ajax so it stores callbacks sent for each outcome
  jqueryAJAXReturnObj = {
    callbacks: {},
    done: function (callback) {
      this.callbacks.done = callback;
      return jqueryAJAXReturnObj;
    },
    fail: function (callback) {
      this.callbacks.fail = callback;
      return jqueryAJAXReturnObj;
    }
  };

  $.ajax.mockImplementation(() => jqueryAJAXReturnObj);

  // RollupJS assigns our bundled module code, including morphdom, to window.GOVUK.
  // morphdom is assigned to its vendor property so we need to copy that here for the updateContent
  // code to pick it up.
  window.GOVUK.vendor = {
    morphdom: require('morphdom')
  };
  require('../../app/assets/javascripts/updateContent.js');

});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Update content', () => {

  const getInitialHTMLString = partial => `
    <div data-notify-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}">
      ${partial}
    </div>`;

  describe("All variations", () => {

    beforeEach(() => {

      // Intentionally basic example because we're not testing changes to the partial
      document.body.innerHTML = getInitialHTMLString(`<p class="notification-status">Sending</p>`);

      // default the response to match the content inside div[data-notify-module]
      responseObj[updateKey] = `<p class="notification-status">Sending</p>`;

    });

    describe("By default", () => {

      beforeEach(() => {

        // start the module
        window.GOVUK.notifyModules.start();

      });

      afterEach(() => {

        // Force last request made to complete, to tidy up for future tests
        forceRequestCompletion();

      });

      test("It should use the GET HTTP method", () => {

        jest.advanceTimersByTime(2000);
        expect($.ajax.mock.calls[0][1].method).toEqual('get');

      });

      test("It shouldn't send any data as part of the requests", () => {

        jest.advanceTimersByTime(2000);
        expect($.ajax.mock.calls[0][1].data).toEqual({});

      });

      test("It should request updates with a dynamic interval", () => {

        // Time from start of module: 1999ms
        // First call doesn’t happen in the first 1999ms
        jest.advanceTimersByTime(1999);
        expect($.ajax).toHaveBeenCalledTimes(0);

        // Time from start of module: 2000ms
        // But it happens at 2000ms by default, before the polling interval becomes dynamic
        jest.advanceTimersByTime(1);
        expect($.ajax).toHaveBeenCalledTimes(1);

        // Time from start of module: 3000ms
        // Simulate server responding 1000ms after request is made
        // This should adjust the polling interval, used next time a request is made
        jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
        serverResponse.complete();

        // Time from start of module: 4000ms
        // Second call happens 2000ms after first request is made as still using the default interval
        jest.advanceTimersByTime(1000);
        expect($.ajax).toHaveBeenCalledTimes(2);

        // Time from start of module: 5000ms
        // Simulate server responding 1000ms after second request is made
        jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
        serverResponse.complete();

        // Time from start of module: 10904ms
        // Third call happens after a 6905ms polling interval, which is based on a response time of 1000ms
        // so shouldn't have happened by 6904ms
        jest.advanceTimersByTime(5904);
        expect($.ajax).toHaveBeenCalledTimes(2);

        // Time from start of module: 10905ms
        // But it should happen at 6905ms
        jest.advanceTimersByTime(1);
        expect($.ajax).toHaveBeenCalledTimes(3);

      });

      each([
        [1000, 0],
        [1500, 100],
        [4590, 500],
        [6905, 1000],
        [24000, 10000],
      ]).test('It calculates a delay of %dms if the API responds in %dms', (waitTime, responseTime) => {
          expect(
            window.GOVUK.NotifyModules.UpdateContent.calculateBackoff(responseTime)
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
        window.GOVUK.notifyModules.start();

      });

      afterEach(() => {

        // Force last request made to complete, to tidy up for future tests
        forceRequestCompletion();

      });

      test("requests should use the same HTTP method as the form", () => {

        jest.advanceTimersByTime(2000);
        expect($.ajax.mock.calls[0][1].method).toEqual('post');

      })

      test("requests should use the data from the form", () => {

        jest.advanceTimersByTime(2000);
        expect($.ajax.mock.calls[0][1].data).toEqual(helpers.getFormDataFromPairs([
          ['serviceName', 'Buckhurst surgery'],
          ['serviceNumber', serviceNumber]
        ]));

      })

    });

    test('With a 401 response status code, polling should be stopped', () => {

      const locationMock = new helpers.LocationMock();

      window.location.reload = jest.fn();

      // start the module
      window.GOVUK.notifyModules.start();

      expect($.ajax).toHaveBeenCalledTimes(0);

      // Time from start of module: 2000ms
      // First call from polling happens at 2000ms
      jest.advanceTimersByTime(2000);
      expect($.ajax).toHaveBeenCalledTimes(1);

      // Time from start of module: 3000ms
      // Simulate server responding 1000ms after request is made with a 401
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.statusCode = 401;
      serverResponse.complete();

      // We expect the 401 to trigger a page reload, to force a redirect to the sign in page
      expect(window.location.reload).toHaveBeenCalled();

      // Tidy up
      locationMock.reset();
      serverResponse.statusCode = 200;
      forceRequestCompletion();

    });

    test('With response.stop === 1, polling should be stopped', () => {
      // start the module
      window.GOVUK.notifyModules.start();

      expect($.ajax).toHaveBeenCalledTimes(0);

      // Time from start of module: 2000ms
      // First call from polling happens at 2000ms
      jest.advanceTimersByTime(2000);
      expect($.ajax).toHaveBeenCalledTimes(1);

      // Time from start of module: 3000ms
      // Simulate server responding 1000ms after request is made with the stop flag set in its payload
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      responseObj.stop = 1;
      serverResponse.complete();

      // Time from start of module: 4000ms
      // Second call happens 2000ms after request is made as polling is still using the default interval
      jest.advanceTimersByTime(1000);

      // We expect all future requests to be blocked by the last one having the stop flag set
      expect($.ajax).toHaveBeenCalledTimes(1);

      // Tidy up
      delete responseObj.stop;
      forceRequestCompletion();
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

    afterEach(() => {

      // Force last request made to complete, to tidy up for future tests
      forceRequestCompletion();

    });

    test("It should replace the original HTML with that of the partial, to match that returned from AJAX responses", () => {

      // start the module
      window.GOVUK.notifyModules.start();

      expect(document.querySelector('.ajax-block-container').parentNode.hasAttribute('data-resource')).toBe(false);

    });

    test("It should make requests to the URL specified in the data-resource attribute", () => {

      // start the module
      window.GOVUK.notifyModules.start();

      jest.advanceTimersByTime(2000);

      expect($.ajax.mock.calls[0][0]).toEqual(resourceURL);

    });

    test("If the response contains no changes, the DOM should stay the same", () => {

      // send the done callback a response with updates included
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check a sample DOM node is unchanged
      expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("0");

    });

    test("If the response contains changes, it should update the DOM with them", () => {

      partialData[0].count = 1;

      // send the done callback a response with updates included
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check the right DOM node is updated
      expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("1");

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

    afterEach(() => {

      // Force last request made to complete, to tidy up for future tests
      forceRequestCompletion();

    });

    test("If the response contains no changes, the DOM should stay the same", () => {

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

      // make a response with no changes
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check it has the same number of items
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

    test("If the response adds a node, the DOM should contain that node", () => {

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
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check the node has been added
      expect(document.querySelectorAll('.file-list').length).toEqual(2);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");
      expect(document.querySelectorAll('.file-list h2 a')[1].textContent.trim()).toEqual("Reservoir flooding template");

    });

    test("If the response removes a node, the DOM should not contain that node", () => {

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
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check the node has been removed
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

    test("If other scripts have added classes to the DOM, they should persist through updates to a single component", () => {

      document.body.innerHTML = getInitialHTMLString(getPartial(partialData));

      // mark classes to persist on the partial
      document.querySelector('.ajax-block-container').setAttribute('data-classes-to-persist', 'js-child-has-focus');

      // Add class to indicate focus state of link on parent heading
      document.querySelectorAll('.file-list h2')[0].classList.add('js-child-has-focus');

      // Add an item to trigger an update
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
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // check the class is still there
      expect(document.querySelectorAll('.file-list h2')[0].classList.contains('js-child-has-focus')).toBe(true);

    });

    test("If other scripts have added classes to the DOM, they should persist through updates to multiple components", () => {

      // Create duplicate components in the page
      document.body.innerHTML = getInitialHTMLString(getPartial(partialData)) + "\n" + getInitialHTMLString(getPartial(partialData));

      var partialsInPage = document.querySelectorAll('.ajax-block-container');

      // Mark classes to persist on the partials (2nd is made up)
      partialsInPage[0].setAttribute('data-classes-to-persist', 'js-child-has-focus');
      partialsInPage[1].setAttribute('data-classes-to-persist', 'js-2nd-child-has-focus');

      // Add examples of those classes on each partial (2nd is made up)
      partialsInPage[0].querySelectorAll('.file-list h2')[0].classList.add('js-child-has-focus');
      partialsInPage[1].querySelectorAll('.file-list h2')[0].classList.add('js-2nd-child-has-focus');

      // Add an item to trigger an update
      partialData.push({
        title: "Reservoir flooding template",
        hint: "The local reservoir has flooded. All people within 5 miles should move to a safer location.",
        status: "Waiting for approval",
        areas: [
          "Santa Claus Village, Rovaniemi A",
          "Santa Claus Village, Rovaniemi D"
        ]
      });

      // make all responses have an extra item
      responseObj[updateKey] = getPartial(partialData);

      // start the module
      window.GOVUK.notifyModules.start();

      // move to the time the first request is fired
      jest.advanceTimersByTime(2000);

      // simulate a 200 response
      jest.advanceTimersByTime(serverResponse.responseTimeInMilliseconds);
      serverResponse.complete();

      // re-select in case nodes in partialsInPage have changed
      partialsInPage = document.querySelectorAll('.ajax-block-container');

      // check the classes are still there
      expect(partialsInPage[0].querySelectorAll('.file-list h2')[0].classList.contains('js-child-has-focus')).toBe(true);
      expect(partialsInPage[1].querySelectorAll('.file-list h2')[0].classList.contains('js-2nd-child-has-focus')).toBe(true);

      // check each heading only has the classes assigned to it before updates occurred
      expect(partialsInPage[0].querySelectorAll('.file-list h2')[0].classList.contains('js-2nd-child-has-focus')).toBe(false);
      expect(partialsInPage[1].querySelectorAll('.file-list h2')[0].classList.contains('js-child-has-focus')).toBe(false);

    });

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // tidy up record of mocked AJAX calls
    $.ajax.mockClear();

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

  });

});
