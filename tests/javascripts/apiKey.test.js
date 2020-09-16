const helpers = require('./support/helpers');

afterAll(() => {

  require('./support/teardown.js');

  // clear up methods in the global space
  document.queryCommandSupported = undefined;

});

describe('API key', () => {

  let apiKey = '00000000-0000-0000-0000-000000000000';
  let thing;
  let component;
  let selectionMock;
  let rangeMock;

  const setUpDOM = function (options) {

    // set up DOM
    document.body.innerHTML =`
      <h2 class="api-key__name">
        ${options.thing}
      </h2>
      <div data-module="api-key" data-key="${apiKey}" data-thing="${options.thing}" data-name="${options.name}">
        <span class="api-key__key" aria-live="assertive">
          ${(options.name === options.thing) ? '<span class="govuk-visually-hidden">' + options.thing + ': </span>' : ''}${apiKey}
        </span>
        <span class="api-key__notice" aria-live="assertive"></span>
      </div>`;

  };

  beforeEach(() => {

    // mock objects used to manipulate the page selection
    selectionMock = new helpers.SelectionMock(jest);
    rangeMock = new helpers.RangeMock(jest);

    // plug gaps in JSDOM's API for manipulation of selections
    window.getSelection = jest.fn(() => selectionMock);
    document.createRange = jest.fn(() => rangeMock);

    // plug JSDOM not having execCommand
    document.execCommand = jest.fn(() => {});

    // mock sticky JS
    window.GOVUK.stickAtBottomWhenScrolling = {
      recalculate: jest.fn(() => {})
    }

  });

  test("If copy command isn't available, nothing should happen", () => {

    // fake support for the copy command not being available
    document.queryCommandSupported = jest.fn(command => false);

    require('../../app/assets/javascripts/apiKey.js');

    setUpDOM({ 'thing': 'API key', 'name': 'API key' });

    component = document.querySelector('[data-module=api-key]');

    // start the module
    window.GOVUK.modules.start();

    expect(component.querySelector('button')).toBeNull();

  });

  describe("If copy command is available", () => {

    let componentHeightOnLoad;

    beforeAll(() => {

      // assume copy command is available
      document.queryCommandSupported = jest.fn(command => command === 'copy');

      // force module require to not come from cache
      jest.resetModules();

      require('../../app/assets/javascripts/apiKey.js');

    });

    afterEach(() => {
      screenMock.reset();
    });

    describe("On page load", () => {

      describe("For all variations of the initial HTML", () => {

        beforeEach(() => {

          setUpDOM({ 'thing': 'API key', 'name': 'API key' });

          component = document.querySelector('[data-module=api-key]');

          // set default style for component height (queried by jQuery before checking DOM APIs)
          const stylesheet = document.createElement('style');
          stylesheet.innerHTML = '[data-module=api-key] { height: auto; }'; // set to browser default
          document.getElementsByTagName('head')[0].appendChild(stylesheet);

          componentHeightOnLoad = 50;

          // mock the DOM APIs called for the position & dimension of the component
          screenMock = new helpers.ScreenMock(jest);
          screenMock.setWindow({
            width: 1990,
            height: 940,
            scrollTop: 0
          });
          screenMock.mockPositionAndDimension('component', component, {
            offsetHeight: componentHeightOnLoad,
            offsetWidth: 641,
            offsetTop: 0
          });

          // start the module
          window.GOVUK.modules.start();

        });

        test("It should add a button for copying the key to the clipboard", () => {

          expect(component.querySelector('button')).not.toBeNull();

        });

        test("It should add the 'api-key' class", () => {

          expect(component.classList.contains('api-key')).toBe(true);

        });

        test("It should tell any sticky JS present the page has changed", () => {

          // recalculate forces the sticky JS to recalculate any stored DOM position/dimensions
          expect(window.GOVUK.stickAtBottomWhenScrolling.recalculate).toHaveBeenCalled();

        });

        test("It should set the component's minimum height based on its height when the page loads", () => {

          // to prevent the position of the button moving when the state changes
          expect(window.getComputedStyle(component)['min-height']).toEqual(`${componentHeightOnLoad}px`);

        });

      });

      describe("If it's one of many in the page", () => {

        beforeEach(() => {

          // If 'thing' (what the id is) and 'name' (its specific idenifier on the page) are
          // different, it will be one of others called the same 'thing'.
          setUpDOM({ 'thing': 'ID', 'name': 'Default' });

          component = document.querySelector('[data-module=api-key]');

          // start the module
          window.GOVUK.modules.start();

        });

        // Because it is not the only 'thing' on the page, the id will not have a heading
        // and so needs some prefix text to label it
        test("The id should have a hidden prefix to label what it is", () => {

          const keyPrefix = component.querySelector('.api-key__key .govuk-visually-hidden');
          expect(keyPrefix).not.toBeNull();
          expect(keyPrefix.textContent).toEqual('ID: ');

        });

        test("the button should have a hidden suffix naming the id it is for", () => {

          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(buttonSuffix).not.toBeNull();
          expect(buttonSuffix.textContent).toEqual(' for Default');

        });

      });

      describe("If it's the only one on the page", () => {

        beforeEach(() => {

          // The heading is added if 'thing' (what the id is) has the same value as 'name'
          // (its specific identifier on the page) because this means it can assume it is
          // the only one of its type there
          setUpDOM({ 'thing': 'API key', 'name': 'API key' });

          component = document.querySelector('[data-module=api-key]');

          // start the module
          window.GOVUK.modules.start();

        });

        test("Its button and id shouldn't have extra hidden text to identify them", () => {

          const keyPrefix = component.querySelector('.api-key__key .govuk-visually-hidden');
          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(keyPrefix).toBeNull();
          expect(buttonSuffix).toBeNull();

        })

      });

    });

    describe("If you click the 'Copy API key to clipboard' button", () => {

      describe("For all variations of the initial HTML", () => {

        let keyEl;

        beforeEach(() => {

          setUpDOM({ 'thing': 'API key', 'name': 'API key' });

          // start the module
          window.GOVUK.modules.start();

          component = document.querySelector('[data-module=api-key]');
          keyEl = component.querySelector('.api-key__key');

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        test("The live-region should be shown and its text should confirm the copy action", () => {

          const liveRegion = component.querySelector('.api-key__notice');

          expect(liveRegion.classList.contains('govuk-visually-hidden')).toBe(false);
          expect(liveRegion.textContent.trim()).toEqual(
            expect.stringContaining('Copied to clipboard')
          );

        });

        // The button also says this but its text after being changed is not announced due to being
        // lower priority than the live-region
        test("The live-region should contain some hidden text giving context to the statement shown", () => {

          const liveRegionHiddenText = component.querySelectorAll('.api-key__notice .govuk-visually-hidden');

          expect(liveRegionHiddenText.length).toEqual(2);
          expect(liveRegionHiddenText[0].textContent).toEqual('API key ');
          expect(liveRegionHiddenText[1].textContent).toEqual(', press button to show in page');

        });

        test("It should swap the button for one to show the API key", () => {

          expect(component.querySelector('button').textContent.trim()).toEqual(
            expect.stringContaining('Show API key')
          );

        });

        test("It should remove the id from the page", () => {

          expect(component.querySelector('.api-key__key')).toBeNull();

        });

        test("It should copy the key to the clipboard", () => {

          // it should make a selection (a range) from the contents of the element containing the API key
          expect(rangeMock.selectNodeContents.mock.calls[0]).toEqual([keyEl]);

          // that selection (a range) should be added to that for the page (a selection)
          expect(selectionMock.addRange.mock.calls[0]).toEqual([rangeMock]);

          expect(document.execCommand).toHaveBeenCalled();
          expect(document.execCommand.mock.calls[0]).toEqual(['copy']);

          // reset any methods in the global space
          window.queryCommandSupported = undefined;
          window.getSelection = undefined;
          document.createRange = undefined;

        });

        describe("If you then click the 'Show API key'", () => {

          beforeEach(() => {

            helpers.triggerEvent(component.querySelector('button'), 'click');

          });

          test("It should change the text to show the API key", () => {

            expect(component.querySelector('.api-key__key')).not.toBeNull();

          });

          test("It should swap the button for one to copy the key to the clipboard", () => {

            expect(component.querySelector('button').textContent.trim()).toEqual(
              expect.stringContaining('Copy API key to clipboard')
            );

          })

        });

      });

      describe("If it's one of many in the page", () => {

        beforeEach(() => {

          // If 'thing' (what the id is) and 'name' (its specific idenifier on the page) are
          // different, it will be one of others called the same 'thing'.
          setUpDOM({ 'thing': 'ID', 'name': 'Default' });

          // start the module
          window.GOVUK.modules.start();

          component = document.querySelector('[data-module=api-key]');

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        test("the button should have a hidden suffix naming the id it is for", () => {

          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(buttonSuffix).not.toBeNull();
          expect(buttonSuffix.textContent).toEqual(' for Default');

        });

        test("the copied selection (range) should start after the prefix of the id", () => {

          // that selection (a range) should have a startOffset past the first two nodes:
          // index 0: text node containing the whitespace before the prefix
          // index 1: the prefix node
          expect(rangeMock.setStart).toHaveBeenCalled();
          expect(rangeMock.setStart.mock.calls[0][1]).toEqual(2);

          // reset any methods in the global space
          window.queryCommandSupported = undefined;
          window.getSelection = undefined;
          document.createRange = undefined;

        });

      });

      describe("If it's the only one on the page", () => {

        beforeEach(() => {

          // The heading is added if 'thing' (what the id is) has the same value as 'name'
          // (its specific identifier on the page) because this means it can assume it is
          // the only one of its type there
          setUpDOM({ 'thing': 'API key', 'name': 'API key' });

          // start the module
          window.GOVUK.modules.start();

          component = document.querySelector('[data-module=api-key]');

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        test("Its button and id shouldn't have extra hidden text to identify them", () => {

          const keyPrefix = component.querySelector('.api-key__key .govuk-visually-hidden');
          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(keyPrefix).toBeNull();
          expect(buttonSuffix).toBeNull();

        })

        test("the copied selection (range) should start at the default position", () => {

          // that selection (a range) shouldn't call setStart to avoid the prefix:
          expect(rangeMock.setStart).not.toHaveBeenCalled();

          // reset any methods in the global space
          window.queryCommandSupported = undefined;
          window.getSelection = undefined;
          document.createRange = undefined;

        });

      });

    });

  });

});
