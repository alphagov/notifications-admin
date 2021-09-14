const each = require('jest-each').default;
const jestDateMock = require('jest-date-mock');

const helpers = require('./support/helpers.js');

const serviceNumber = '6658542f-0cad-491f-bec8-ab8457700ead';
const resourceURL = `/services/${serviceNumber}/notifications/email.json?status=sending%2Cdelivered%2Cfailed`;
const updateKey = 'counts';

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
      // The server takes 1 second to respond
      jestDateMock.advanceBy(1000);
      callback(responseObj);
      return jqueryAJAXReturnObj;
    },
    fail: () => {}
  };

  $.ajax.mockImplementation(() => jqueryAJAXReturnObj);

  // because we're running in node, we can't execute the normal domdiff code like a browser because
  // its variables (actually only one: domdiff) stay local to it
  // in the normal browser environment it will attach to window so we replicate that here by using
  // the CommonJS module version and assigning it to window
  window.domdiff = require('domdiff/cjs').default;
  require('../../app/assets/javascripts/updateContent.js');

});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Update content', () => {

  beforeEach(() => {

    // store HTML in string to allow use in AJAX responses
    HTMLString = `
      <div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
        <div class="bottom-gutter ajax-block-container">
          <ul role="tablist" class="pill">
            <li aria-selected="true" role="tab">
              <div class="pill-selected-item" tabindex="0">
                <div class="big-number-smaller">
                  <div class="big-number-number">0</div>
                </div>
                <div class="pill-label">total</div>
              </div>
            </li>
            <li aria-selected="false" role="tab">
              <a class="govuk-link govuk-link--no-visited-state" href="/services/6658542f-0cad-491f-bec8-ab8457700ead/notifications/email?status=sending">
                <div class="big-number-smaller">
                  <div class="big-number-number">0</div>
                </div>
                <div class="pill-label">sending</div>
              </a>
            </li>
            <li aria-selected="false" role="tab">
              <a class="govuk-link govuk-link--no-visited-state" href="/services/6658542f-0cad-491f-bec8-ab8457700ead/notifications/email?status=delivered">
                <div class="big-number-smaller">
                  <div class="big-number-number">0</div>
                </div>
                <div class="pill-label">delivered</div>
              </a>
            </li>
            <li aria-selected="false" role="tab">
              <a class="govuk-link govuk-link--no-visited-state" href="/services/6658542f-0cad-491f-bec8-ab8457700ead/notifications/email?status=failed">
                <div class="big-number-smaller">
                  <div class="big-number-number">0</div>
                </div>
                <div class="pill-label">failed</div>
              </a>
            </li>
          </ul>
        </div>
      </div>`;

    document.body.innerHTML = HTMLString;

    // default the response to match the existing content
    responseObj[updateKey] = HTMLString;

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // tidy up record of mocked AJAX calls
    $.ajax.mockClear();

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

  });

  test("It should make requests to the URL specified in the data-resource attribute", () => {

    // start the module
    window.GOVUK.modules.start();
    jest.advanceTimersByTime(2000);

    expect($.ajax.mock.calls[0][0]).toEqual(resourceURL);

  });

  test("If the response contains no changes, the DOM should stay the same", () => {

    // send the done callback a response with updates included
    responseObj[updateKey] = HTMLString;

    // start the module
    window.GOVUK.modules.start();
    jest.advanceTimersByTime(2000);

    // check the right DOM node is updated
    expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("0");

  });

  test("If the response contains changes, it should update the DOM with them", () => {

    // send the done callback a response with updates included
    responseObj[updateKey] = HTMLString.replace(/<div class="big-number-number">0<\/div>{1}/, '<div class="big-number-number">1</div>');

    // start the module
    window.GOVUK.modules.start();
    jest.advanceTimersByTime(2000);

    // check the right DOM node is updated
    expect(document.querySelectorAll('.big-number-number')[0].textContent.trim()).toEqual("1");

  });

  describe("By default", () => {

    beforeEach(() => {

      // start the module
      window.GOVUK.modules.start();

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

      // First call doesn’t happen in the first 2000ms
      jest.advanceTimersByTime(1999);
      expect($.ajax).toHaveBeenCalledTimes(0);

      // But it happens after 2000ms by default
      jest.advanceTimersByTime(1);
      expect($.ajax).toHaveBeenCalledTimes(1);

      // It took the server 1000ms to respond to the first call so we
      // will back off – the next call shouldn’t happen in the next 6904ms
      jest.advanceTimersByTime(6904);
      expect($.ajax).toHaveBeenCalledTimes(1);

      // But it should happen after 6905ms
      jest.advanceTimersByTime(1);
      expect($.ajax).toHaveBeenCalledTimes(2);

    });

    each([
      [1000, 0],
      [1500, 100],
      [4590, 500],
      [6905, 1000],
      [24000, 10000],
    ]).test('It calculates a delay of %dms if the API responds in %dms', (waitTime, responseTime) => {
        expect(
          window.GOVUK.Modules.UpdateContent.calculateBackoff(responseTime)
        ).toBe(
          waitTime
        );
    });

  });

  describe("If a form is used as a source for data, referenced in the data-form attribute", () => {

    beforeEach(() => {

      document.body.innerHTML += `
        <form method="post" id="service">
          <input type="hidden" name="serviceName" value="Buckhurst surgery" />
          <input type="hidden" name="serviceNumber" value="${serviceNumber}" />
        </form>`;

      document.querySelector('[data-module=update-content]').setAttribute('data-form', 'service');

      // start the module
      window.GOVUK.modules.start();

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

});
