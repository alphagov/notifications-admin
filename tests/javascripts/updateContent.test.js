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

  let HTMLString;
  let initialHTMLString;

  describe('When updating the contents of DOM nodes', () => {

    beforeEach(() => {

      // store HTML in string to allow use in AJAX responses
      HTMLString = `
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
        </div>`;


      initialHTMLString = `<div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
                          ${HTMLString}
                          </div>`;

      document.body.innerHTML = initialHTMLString;

      // default the response to match the content inside div[data-module]
      responseObj[updateKey] = HTMLString;

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

      // check a sample DOM node is unchanged
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

  describe("When adding or removing DOM nodes", () => {
    var getItemHTMLString = content => {
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

    var getHTMLString = items => {

      var itemsHTMLString = '';

      items.forEach(item => itemsHTMLString += "\n" + getItemHTMLString(item));

      return `<div class="ajax-block-container">
                ${itemsHTMLString};
                <div class="keyline-block"></div>
              </div>`;

    };

    test("If the response contains no changes, the DOM should stay the same", () => {

      // store HTML in string to allow use in AJAX responses
      HTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        }
      ]);

      initialHTMLString = `<div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
                          ${HTMLString}
                          </div>`;

      document.body.innerHTML = initialHTMLString;

      // make the response have an extra item
      responseObj[updateKey] = HTMLString;

      // start the module
      window.GOVUK.modules.start();
      jest.advanceTimersByTime(2000);

      // check it has the same number of items
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

    test("If the response adds a node, the DOM should contain that node", () => {

      // store HTML in string to allow use in AJAX responses
      HTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        }
      ]);

      initialHTMLString = `<div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
                          ${HTMLString}
                          </div>`;

      document.body.innerHTML = initialHTMLString;

      var updatedHTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        },
        {
          title: "Reservoir flooding template",
          hint: "The local reservoir has flooded. All people within 5 miles should move to a safer location.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi A",
            "Santa Claus Village, Rovaniemi D"
          ]
        }
      ]);

      // make the response have an extra item
      responseObj[updateKey] = updatedHTMLString;

      // start the module
      window.GOVUK.modules.start();
      jest.advanceTimersByTime(2000);

      // check the node has been added
      expect(document.querySelectorAll('.file-list').length).toEqual(2);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");
      expect(document.querySelectorAll('.file-list h2 a')[1].textContent.trim()).toEqual("Reservoir flooding template");

    });

    test("If the response removes a node, the DOM should not contain that node", () => {

      // store HTML in string to allow use in AJAX responses
      HTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        },
        {
          title: "Reservoir flooding template",
          hint: "The local reservoir has flooded. All people within 5 miles should move to a safer location.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi A",
            "Santa Claus Village, Rovaniemi D"
          ]
        }
      ]);

      initialHTMLString = `<div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
                          ${HTMLString}
                          </div>`;

      document.body.innerHTML = initialHTMLString;

      var updatedHTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        }
      ]);

      // default the response to match the content inside div[data-module]
      responseObj[updateKey] = updatedHTMLString;

      // start the module
      window.GOVUK.modules.start();
      jest.advanceTimersByTime(2000);

      // check the node has been removed
      expect(document.querySelectorAll('.file-list').length).toEqual(1);
      expect(document.querySelectorAll('.file-list h2 a')[0].textContent.trim()).toEqual("Gas leak");

    });

    test("If other scripts have added classes to the DOM, they should persist through updates", () => {

      // store HTML in string to allow use in AJAX responses
      HTMLString = getHTMLString([
        {
          title: "Gas leak",
          hint: "There's a gas leak in the local area. Residents should vacate until further notice.",
          status: "Waiting for approval",
          areas: [
            "Santa Claus Village, Rovaniemi B",
            "Santa Claus Village, Rovaniemi C"
          ]
        }
      ]);

      initialHTMLString = `<div data-module="update-content" data-resource="${resourceURL}" data-key="${updateKey}" aria-live="polite">
                          ${HTMLString}
                          </div>`;

      document.body.innerHTML = initialHTMLString;

      // mark classes to persist on the partial
      document.querySelector('.ajax-block-container').setAttribute('data-classes-to-persist', 'js-child-has-focus');

      // Add class to indicate focus state of link on parent heading
      document.querySelectorAll('.file-list h2')[0].classList.add('js-child-has-focus');

      // make the response match the initial HTML to emulate a response with no changes
      responseObj[updateKey] = HTMLString;

      // start the module
      window.GOVUK.modules.start();
      jest.advanceTimersByTime(2000);

      // check the class is still there
      expect(document.querySelectorAll('.file-list h2')[0].classList.contains('js-child-has-focus')).toBe(true);

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
