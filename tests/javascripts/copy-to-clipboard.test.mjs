import * as helpers from './support/helpers.js';
import CopyToClipboard from '../../app/assets/javascripts/esm/copy-to-clipboard.mjs';
import { beforeEach, jest } from '@jest/globals';


beforeAll(() => {
  document.body.classList.add('govuk-frontend-supported');
});

describe('copy to clipboard', () => {

  let apiKey = '00000000-0000-0000-0000-000000000000';
  let thing;
  let component;
  let rangeMock;

  const setUpDOM = function (options) {

    // set up DOM
    document.body.innerHTML =`
      <h2 class="copy-to-clipboard__name">
        ${options.thing}
      </h2>
      <div data-notify-module="copy-to-clipboard" data-value="${apiKey}" data-thing="${options.thing}" data-name="${options.name}">
        <span class="copy-to-clipboard__value" aria-live="assertive">${(options.name === options.thing) ? '<span class="govuk-visually-hidden">' + options.thing + ': </span>' : ''}${apiKey}</span>
        <span class="copy-to-clipboard__notice" aria-live="assertive"></span>
      </div>`;

  };

  beforeEach(() => {
    // mock objects used to manipulate the page selection
    rangeMock = new helpers.RangeMock(jest);

    // plug gaps in JSDOM's API for Range
    document.createRange = jest.fn(() => rangeMock);

    // mock sticky JS
    window.GOVUK.stickAtBottomWhenScrolling = {
      recalculate: jest.fn(() => {})
    }

  });

  test("If Clipboard API isn't supported, nothing should happen", () => {

    // fake Clipboard API not being available
    navigator.clipboard = false

    setUpDOM({ 'thing': 'Some Thing', 'name': 'Some Thing' });

    component = document.querySelector('[data-notify-module=copy-to-clipboard]');

    // start the module
    new CopyToClipboard(component);

    expect(component.querySelector('button')).toBeNull();

  });

  describe("If Clipboard API is supported", () => {

    beforeAll(() => {
      // force module require to not come from cache
      jest.resetModules();

    });

    beforeEach(() => {
      // mock Clipboard API availability
      Object.assign(navigator, {
        clipboard: { 
          writeText: jest.fn().mockImplementation(() => Promise.resolve()),
        },
      });

    })

    describe("On page load", () => {

      describe("For all variations of the initial HTML", () => {

        beforeEach(() => {

          setUpDOM({ 'thing': 'Some Thing', 'name': 'Some Thing' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');

          // start the module
          new CopyToClipboard(component);

        });

        test("It should add a button for copying the thing to the clipboard", () => {

          expect(component.querySelector('button')).not.toBeNull();

        });

        test("It should add the 'copy-to-clipboard' class", () => {

          expect(component.classList.contains('copy-to-clipboard')).toBe(true);

        });

        test("It should tell any sticky JS present the page has changed", () => {

          // recalculate forces the sticky JS to recalculate any stored DOM position/dimensions
          expect(window.GOVUK.stickAtBottomWhenScrolling.recalculate).toHaveBeenCalled();

        });

        test("It should render the 'thing' without extra whitespace", () => {

          expect(component.querySelector('.copy-to-clipboard__value').textContent).toBe('00000000-0000-0000-0000-000000000000');

        });

      });

      describe("If it's one of many in the page", () => {

        beforeEach(() => {

          // If 'thing' (what the id is) and 'name' (its specific idenifier on the page) are
          // different, it will be one of others called the same 'thing'.
          setUpDOM({ 'thing': 'ID', 'name': 'Default' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');

          // start the module
          new CopyToClipboard(component);

        });

        // Because it is not the only 'thing' on the page, the id will not have a heading
        // and so needs some prefix text to label it
        test("The id should have a hidden prefix to label what it is", () => {

          const value = component.querySelector('.copy-to-clipboard__value .govuk-visually-hidden');
          expect(value).not.toBeNull();
          expect(value.textContent).toEqual('ID: ');

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
          setUpDOM({ 'thing': 'Some Thing', 'name': 'Some Thing' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');

          // start the module
          new CopyToClipboard(component);

        });

        test("Its button and id shouldn't have extra hidden text to identify them", () => {

          const value = component.querySelector('.copy-to-clipboard__value .govuk-visually-hidden');
          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(value).toBeNull();
          expect(buttonSuffix).toBeNull();

        })

      });

      test("It should add a button for copying the thing to the clipboard", () => {

        setUpDOM({ 'thing': 123456, 'name': 987654 });

        component = document.querySelector('[data-notify-module=copy-to-clipboard]');

        // start the module
        new CopyToClipboard(component);

        expect(component.querySelector('button')).not.toBeNull();

      });

    });

    describe("If you click the 'Copy Some Thing to clipboard' button", () => {

      describe("For all variations of the initial HTML", () => {

        let keyEl;
        const originalClipboard = navigator.clipboard;

        beforeEach(() => {

          setUpDOM({ 'thing': 'Some Thing', 'name': 'Some Thing' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');
          // start the module
          new CopyToClipboard(component);

          keyEl = component.querySelector('.copy-to-clipboard__value');

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        afterEach(() => {
          // reset clipboard to original state
          navigator.clipboard = originalClipboard;
        })

        test("The live-region should be shown and its text should confirm the copy action", () => {

          const liveRegion = component.querySelector('.copy-to-clipboard__notice');

          expect(liveRegion.classList.contains('govuk-visually-hidden')).toBe(false);
          expect(liveRegion.textContent.trim()).toEqual(
            expect.stringContaining('Copied to clipboard')
          );

        });

        // The button also says this but its text after being changed is not announced due to being
        // lower priority than the live-region
        test("The live-region should contain some hidden text giving context to the statement shown", () => {

          const liveRegionHiddenText = component.querySelectorAll('.copy-to-clipboard__notice .govuk-visually-hidden');

          expect(liveRegionHiddenText.length).toEqual(2);
          expect(liveRegionHiddenText[0].textContent).toEqual('Some Thing ');
          expect(liveRegionHiddenText[1].textContent).toEqual(', use button to show in page');

        });

        test("It should swap the button for one to show the Some Thing", () => {

          expect(component.querySelector('button').textContent.trim()).toEqual(
            expect.stringContaining('Show Some Thing')
          );

        });

        test("It should remove the id from the page", () => {

          expect(component.querySelector('.copy-to-clipboard__value')).toBeNull();

        });

        test("It should copy the thing to the clipboard", () => {

          // it should make a selection (a range) from the contents of the element containing the Some Thing
          expect(rangeMock.selectNodeContents.mock.calls[0]).toEqual([keyEl]);

          // that selection (a range) should be added to that for the page (a selection)
          expect(window.navigator.clipboard.writeText).toHaveBeenCalledWith(rangeMock);

          // reset any methods in the global space
          document.createRange = undefined;

        });

        describe("If you then click the 'Show Some Thing'", () => {

          beforeEach(() => {

            helpers.triggerEvent(component.querySelector('button'), 'click');

          });

          test("It should change the text to show the Some Thing", () => {

            expect(component.querySelector('.copy-to-clipboard__value')).not.toBeNull();

          });

          test("It should swap the button for one to copy the thing to the clipboard", () => {

            expect(component.querySelector('button').textContent.trim()).toEqual(
              expect.stringContaining('Copy Some Thing to clipboard')
            );

          })

        });

      });

      describe("If it's one of many in the page", () => {

        beforeEach(() => {

          // If 'thing' (what the id is) and 'name' (its specific idenifier on the page) are
          // different, it will be one of others called the same 'thing'.
          setUpDOM({ 'thing': 'ID', 'name': 'Default' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');

          // start the module
          new CopyToClipboard(component);

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        test("the button should have a hidden suffix naming the id it is for", () => {

          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(buttonSuffix).not.toBeNull();
          expect(buttonSuffix.textContent).toEqual(' for Default');

        });

        test("the copied selection (range) should start after visually hidden prefix", () => {

          // that selection (a range) should have a startOffset of 1:
          // index 0: the visually hidden prefix node, for example "Template ID: " or "API key: "
          // index 1: the value node
          expect(rangeMock.setStart).toHaveBeenCalled();
          expect(rangeMock.setStart.mock.calls[0][1]).toEqual(1);

          // reset any methods in the global space
          document.createRange = undefined;

        });

      });

      describe("If it's the only one on the page", () => {

        beforeEach(() => {

          // The heading is added if 'thing' (what the id is) has the same value as 'name'
          // (its specific identifier on the page) because this means it can assume it is
          // the only one of its type there
          setUpDOM({ 'thing': 'Some Thing', 'name': 'Some Thing' });

          component = document.querySelector('[data-notify-module=copy-to-clipboard]');

          // start the module
          new CopyToClipboard(component);

          helpers.triggerEvent(component.querySelector('button'), 'click');

        });

        test("Its button and id shouldn't have extra hidden text to identify them", () => {

          const prefix = component.querySelector('.copy-to-clipboard__value .govuk-visually-hidden');
          const buttonSuffix = component.querySelector('button .govuk-visually-hidden');
          expect(prefix).toBeNull();
          expect(buttonSuffix).toBeNull();

        })

        test("the copied selection (range) should start at the default position", () => {

          // that selection (a range) shouldn't call setStart to avoid the prefix:
          expect(rangeMock.setStart).not.toHaveBeenCalled();

          // reset any methods in the global space
          document.createRange = undefined;

        });

      });

    });

  });

});
