const helpers = require('./support/helpers');
const PADDING_BETWEEN_STICKYS = 40;
const PADDING_BEFORE_STOPPING_POINT = 10;

function getScreenItemBottomPosition (screenItem) {
  return screenItem.offsetTop + screenItem.offsetHeight;
};

function getCaretPosition (caretPosition, textarea) {

  return {
    top: textarea.offsetTop + caretPosition.top,
    bottom: textarea.offsetTop + caretPosition.top + caretPosition.height,
    height: caretPosition.height
  };

};

function getStickyGroupPosition (screenMock, opts) {

  const edgePosition = screenMock.window[opts.edge];
  const height = opts.stickyEls
                  .map(el => el.offsetHeight)
                  .reduce((accumulator, height) => accumulator + height);

  if (opts.edge === 'top') {
    return {
      top: screenMock.window.top,
      bottom: edgePosition + height,
      height: height
    };
  } else {
    return {
      top: edgePosition - height,
      bottom: screenMock.window.bottom,
      height: height
    }
  }

};

class CaretCoordinates {
  constructor (data) {
    this.top = 5.5;
    this.left = 2;
    this.height = 19;
  }

  moveToLine (lineNumber) {
    const lineHeight = 30;
    const verticalPadding = 5.5;

    this.top = ((lineNumber - 1) * lineHeight) + verticalPadding;
  }
}

beforeAll(() => {
  require('../../app/assets/javascripts/stick-to-window-when-scrolling.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe("Stick to top/bottom of window when scrolling", () => {

  let screenMock;

  describe("If intending to stick to the top", () => {

    let inputForm;
    let formFooter;
    let footer;
    let windowHeight;
    let getFurthestTopPoint;

    beforeEach(() => {

      document.body.innerHTML = `
        <div class="govuk-grid-row">
          <main class="govuk-grid-column-three-quarters column-main">
            <form method="post" autocomplete="off">
              <div class="govuk-grid-row js-stick-at-top-when-scrolling">
                <div class="govuk-grid-column-two-thirds ">
                  <div class="form-group" data-module="">
                    <label class="form-label" for="placeholder_value">
                      name
                    </label>
                    <input class="form-control form-control-1-1 " data-module="" id="placeholder_value" name="placeholder_value" required="" rows="8" type="text" value="">
                  </div>
                </div>
              </div>
              <div class="page-footer">
                <button type="submit" class="govuk-button">Continue</button>
              </div>
            </form>
          </main>
        </div>
        <footer class="js-footer"></footer>`;

      inputForm = document.querySelector('form > .govuk-grid-row');
      formFooter = document.querySelector('.page-footer');
      footer = document.querySelector('.js-footer');

      windowHeight = 940;

      // mock the rendering of all components
      screenMock = new helpers.ScreenMock(jest);
      screenMock.setWindow({
        width: 1990,
        height: windowHeight,
        scrollTop: 0
      });
      screenMock.mockPositionAndDimension('inputForm', inputForm, {
        offsetHeight: 168,
        offsetWidth: 727,
        offsetTop: 238
      });
      screenMock.mockPositionAndDimension('formFooter', formFooter, {
        offsetHeight: 200,
        offsetWidth: 727,
        offsetTop: inputForm.offsetTop + 200
      });
      screenMock.mockPositionAndDimension('footer', footer, {
        offsetHeight: 535,
        offsetWidth: 1990,
        offsetTop: formFooter.offsetTop + formFooter.offsetHeight
      });

      getFurthestTopPoint = (stickysHeight) => {
        return footer.offsetTop - PADDING_BEFORE_STOPPING_POINT - stickysHeight;
      };

      // the sticky JS polls for changes to position/dimension so we need to fake setTimeout and setInterval
      jest.useFakeTimers();

    });

    afterEach(() => {

      document.body.innerHTML = '';

      window.GOVUK.stickAtTopWhenScrolling.clearEvents();

      screenMock.reset();

    });

    test("if top of viewport is above top of element on load, the element should not be marked as sticky", () => {

      // scroll position defaults to 0, element top defaults to 138px

      window.GOVUK.stickAtTopWhenScrolling.init();

      expect(inputForm.classList.contains('content-fixed-onload')).toBe(false);
      expect(inputForm.classList.contains('content-fixed')).toBe(false);

    });

    test("if the window is 768px or less wide and the top of the viewport is below top of element on load, the element should not be marked as sticky", () => {

      screenMock.window.resizeTo({
        height: windowHeight,
        width: 768
      });

      // scroll past top of form
      screenMock.scrollTo(inputForm.offsetTop + 10);

      window.GOVUK.stickAtTopWhenScrolling.init();

      expect(inputForm.classList.contains('content-fixed')).toBe(false);
      expect(inputForm.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

    });

    describe("if top of viewport is below top of element but still in the scroll area on load", () => {

      beforeEach(() => {

        // scroll past the top of the form
        screenMock.scrollTo(inputForm.offsetTop + 10);

        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      test("the element should be marked as already sticky", () => {

        // `.content-fixed-onload` adds the drop-shadow without fading in to show it did not become sticky from user interaction
        expect(inputForm.classList.contains('content-fixed-onload')).toBe(true);
        expect(inputForm.classList.contains('content-fixed')).toBe(false);

      });

      test("a 'shim' element with dimensions matching the sticky element should be added to the document to take up the space it no longer occupies", () => {

        const shim = inputForm.previousElementSibling;

        expect(shim).not.toBeNull();
        expect(shim.classList.contains('shim')).toBe(true);
        expect(shim.style.height).toEqual(`${inputForm.offsetHeight}px`);
        expect(shim.style.marginTop).toEqual(''); // 0px would return an empty string
        expect(shim.style.marginBottom).toEqual(''); // 0px would return an empty string

      });

    });

    test("if top of viewport is below the furthest point the top of the element can go in the scroll area on load, the element should be marked as stopped", () => {

      // the element should stop a set distance from the stopping point
      const furthestTopPoint = getFurthestTopPoint(inputForm.offsetHeight);

      // scroll past the furthest point
      screenMock.scrollTo(furthestTopPoint + 10);

      window.GOVUK.stickAtTopWhenScrolling.init();

      // `.content-fixed-onload` adds the drop-shadow without fading in to show it did not become sticky from user interaction
      expect(inputForm.classList.contains('content-fixed-onload')).toBe(true);
      expect(inputForm.classList.contains('content-fixed')).toBe(false);

      // elements are stopped by adding inline styles
      expect(inputForm.style.position).toEqual('absolute');
      expect(inputForm.style.top).toEqual(`${furthestTopPoint}px`);

    });

    describe("if viewport top starts above element top", () => {

      beforeEach(() => {

        // default scroll position is above top of form
        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      test("if window is scrolled so top of it is below the top of the element, the element should be marked so it becomes sticky to the user", () => {

        // scroll past top of form
        screenMock.scrollTo(inputForm.offsetTop + 10);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        // `content-fixed` fades the drop-shadow in to show it became sticky from user interaction
        expect(inputForm.classList.contains('content-fixed')).toBe(true);
        expect(inputForm.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

      });

      test("if window is scrolled so top of it is below the furthest point the top of the element can go in the scroll area, the element should be stopped", () => {

        const furthestTopPoint = getFurthestTopPoint(inputForm.offsetHeight);

        // scroll past top of form
        screenMock.scrollTo(furthestTopPoint + 10);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        // `content-fixed` fades the drop-shadow in to show it became sticky from user interaction
        expect(inputForm.classList.contains('content-fixed')).toBe(true);
        expect(inputForm.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

        // elements are stopped by adding inline styles
        expect(inputForm.style.position).toEqual('absolute');
        expect(inputForm.style.top).toEqual(`${furthestTopPoint}px`);

      });

    });

    describe("if viewport top starts below element top", () => {

      beforeEach(() => {

        // scroll past top of form
        screenMock.scrollTo(inputForm.offsetTop + 10);

        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      test("if window is scrolled so top of it is above the top of the element, the element should be made not sticky", () => {

        // scroll to top
        screenMock.scrollTo(0);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        expect(inputForm.classList.contains('content-fixed')).toBe(false);
        expect(inputForm.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

      });

    });

    describe("if scrollToRevealElement is called with an element", () => {

      let link;
      let linkBottom;

      beforeEach(() => {

        const inputFormBottom = getScreenItemBottomPosition(inputForm);

        inputForm.insertAdjacentHTML('afterEnd', '<a href="" id="formatting-options">Formatting options</a>');
        link = document.querySelector('#formatting-options');

        screenMock.mockPositionAndDimension('link', link, {
          offsetHeight: 25, // 143px smaller than the sticky
          offsetWidth: 727,
          offsetTop: inputFormBottom
        });

        linkBottom = getScreenItemBottomPosition(link);

        // move the sticky over the link. It's 168px high so this position will cause it to overlap.
        screenMock.scrollTo(link.offsetTop - 140);

        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();

      });

      test("the window should scroll so the element is revealed", () => {

        // update inputForm position as DOM normally would
        inputForm.offsetTop = screenMock.window.top;

        let stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });

        // sticky position should overlap link position
        expect(stickyPosition.top).toBeLessThanOrEqual(link.offsetTop);
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(linkBottom);

        window.GOVUK.stickAtTopWhenScrolling.scrollToRevealElement(link);

        stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });

        // the bottom of the sticky element should be at the top of the link
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, link.offsetTop - stickyPosition.height]);

      });

    });

    describe("if element is made sticky and another element underneath it is focused", () => {

      let checkbox;
      let checkboxBottom;

      beforeEach(() => {

        const inputFormBottom = getScreenItemBottomPosition(inputForm);

        inputForm.insertAdjacentHTML('afterEnd', '<input type="checkbox" name="confirm" value="yes" />');
        checkbox = document.querySelector('input[type=checkbox]');

        screenMock.mockPositionAndDimension('checkbox', checkbox, {
          offsetHeight: 50, // 118px smaller than the sticky
          offsetWidth: 727,
          offsetTop: inputFormBottom
        });

        checkboxBottom = getScreenItemBottomPosition(checkbox);

        // move the sticky over the checkbox. It's 168px high so this position will cause it to overlap.
        screenMock.scrollTo(checkbox.offsetTop - 10);

        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();

      });

      test("the window should scroll so the focused element is revealed", () => {

        // update inputForm position as DOM normally would
        inputForm.offsetTop = screenMock.window.top;

        let stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });

        // sticky position should overlap checkbox position
        expect(stickyPosition.top).toBeLessThanOrEqual(checkbox.offsetTop);
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(checkboxBottom);

        // the sticky element (page footer) is 50 high so should cover the last of the radios if the bottom edge of the viewport is at its bottom
        checkbox.focus();

        stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });

        // the bottom of the sticky element should be at the top of the checkbox
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, checkbox.offsetTop - stickyPosition.height]);

      });

    });

    describe("if element is made sticky and overlaps a textarea", () => {

      let textarea;
      let textareaBottom;
      let caretCoordinates;
      let caretCoordinatesMock;

      beforeEach(() => {

        const inputFormBottom = getScreenItemBottomPosition(inputForm);

        inputForm.insertAdjacentHTML('afterEnd', '<textarea name="notes"></textarea>');
        textarea = document.querySelector('textarea');

        // line height: 30px, text height: 19px, lines: 10
        screenMock.mockPositionAndDimension('textarea', textarea, {
          offsetHeight: 300,
          offsetWidth: 727,
          offsetTop: inputFormBottom
        });

        textareaBottom = getScreenItemBottomPosition(textarea);

        // mock calls for caret position, relative to textarea
        caretCoordinatesMock = jest.fn(() => caretCoordinates);
        window.getCaretCoordinates = caretCoordinatesMock;

        // start caret on first line
        caretCoordinates = new CaretCoordinates();

        // move the sticky so it overlaps the top 168px of the textarea.
        screenMock.scrollTo(textarea.offsetTop);

        // update inputForm position as DOM normally would
        inputForm.offsetTop = screenMock.window.top;

        window.GOVUK.stickAtTopWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();
        caretCoordinatesMock.mockClear();

      });

      test("if the textarea receives focus while its caret is underneath, the window should scroll to reveal the caret", () => {

        // caret is on first line
        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // sticky position should overlap caret position
        expect(stickyPosition.top).toBeLessThanOrEqual(caretPosition.top);
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(caretPosition.bottom);

        // the sticky element (page footer) is 50 high so should cover the last of the radios if the bottom edge of the viewport is at its bottom
        textarea.focus();

        // the bottom of the sticky element should be at the top of the checkbox
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, caretPosition.top - stickyPosition.height]);

      });

      test("if the caret is moved so it isn't underneath the sticky element, the window shouldn't scroll", () => {

        // start caret on 7th line which isn't under the sticky element.
        caretCoordinates.moveToLine(7);

        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // the sticky element should be above the caret
        expect(stickyPosition.bottom).toBeLessThan(caretPosition.top);

        textarea.focus();

        // no scrolling should have happened
        expect(screenMock.window.spies.window.scrollTo.mock.calls.length).toEqual(0);

      });

      test("if the caret is moved to be underneath the sticky element, the window should scroll to reveal the caret", () => {

        // start caret on 7th line which isn't under the sticky element.
        caretCoordinates.moveToLine(7);

        // make sure the textarea has focus
        textarea.focus();

        // line 6 is under the sticky element
        caretCoordinates.moveToLine(6);

        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [inputForm], edge: 'top' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // sticky should now overlap the caret
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(caretPosition.top);

        // the sticky element (page footer) is 50 high so should cover the last of the radios if the bottom edge of the viewport is at its bottom
        helpers.triggerEvent(textarea, 'keyup', { interface: window.KeyboardEvent });

        // the bottom of the sticky element should be at the top of the checkbox
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, caretPosition.top - stickyPosition.height]);

      });

    });

    describe("if mode is set to 'dialog' and multiple sticky elements share the same scroll area", () => {

      let radios;

      beforeEach(() => {

        const inputFormBottom = getScreenItemBottomPosition(inputForm);

        // set mode to 'dialog' so sticky elements are treated as one item
        window.GOVUK.stickAtTopWhenScrolling.setMode('dialog')

        // add another sticky element before the form footer
        radios = helpers.getRadioGroup({
          cssClasses: ['js-stick-at-top-when-scrolling'],
          name: 'choose-send-time',
          label: 'Choose send time',
          fields: [
            {
              label: 'Now',
              value: 'now',
              checked: true
            },
            {
              label: 'Tomorrow',
              value: 'tomorrow',
              checked: false
            },
            {
              label: 'Friday',
              value: 'friday',
              checked: false
            }
          ]
        });
        formFooter.parentNode.insertBefore(radios, formFooter);
        screenMock.mockPositionAndDimension('radios', radios, {
          offsetHeight: 175,
          offsetWidth: 727,
          offsetTop: inputFormBottom
        });
        const radiosBottom = getScreenItemBottomPosition(radios);

        // adjust other screen items

        // formFooter top should be at the radios bottom
        formFooter.offsetTop = radiosBottom;

        // footer top should be at formFooter's bottom
        footer.offsetTop = getScreenItemBottomPosition(formFooter);

      });

      afterEach(() => {

        window.GOVUK.stickAtTopWhenScrolling.setMode('default');

      });

      describe("if window top is below the top of the highest element on load", () => {

        beforeEach(() => {

          // scroll past top of first sticky element
          screenMock.scrollTo(inputForm.offsetTop + 10);

          window.GOVUK.stickAtTopWhenScrolling.init();

        });

        test("both should be marked as already sticky", () => {

          // `.content-fixed-onload` adds the drop-shadow without fading in to show it did not become sticky from user interaction
          expect(radios.classList.contains('content-fixed-onload')).toBe(true);
          expect(radios.classList.contains('content-fixed')).toBe(false);
          expect(inputForm.classList.contains('content-fixed-onload')).toBe(true);
          expect(inputForm.classList.contains('content-fixed')).toBe(false);

        });

        test("the lowest element should have the drop-shadow", () => {

          expect(radios.classList.contains('content-fixed__top')).toBe(true);

        });

        test("they should be stacked from the top edge of the viewport in the order they appear in the document", () => {

          expect(inputForm.style.top).toEqual('0px');

          // dialog mode removes enough padding to deal with that each sticky element is given to give its content enough space from the surrounding page
          expect(radios.style.top).toEqual(`${inputForm.offsetHeight - PADDING_BETWEEN_STICKYS}px`);

        });

      });

      describe("if window top is below the furthest point the highest element can go on load", () => {

        let furthestTopPoint;

        beforeEach(() => {

          // ensure each sticky element is positioned correctly relative to the furthest point
          const dialogHeight = (inputForm.offsetHeight + radios.offsetHeight) - PADDING_BETWEEN_STICKYS;

          furthestTopPoint = getFurthestTopPoint(dialogHeight);

          // scroll past top of first sticky element
          screenMock.scrollTo(furthestTopPoint + 10);

          window.GOVUK.stickAtTopWhenScrolling.init();

        });

        test("both should be stopped so the bottom of their stack is at the furthest point", () => {

          expect(inputForm.style.position).toEqual('absolute');
          expect(radios.style.position).toEqual('absolute');

          expect(inputForm.style.top).toEqual(`${furthestTopPoint}px`);
          expect(radios.style.top).toEqual(`${footer.offsetTop - PADDING_BEFORE_STOPPING_POINT - radios.offsetHeight}px`);

        });

      });

      describe("if the group of sticky elements is taller than the window when stuck together", () => {

        // the sticky behaviour should stick as many elements as possible to the top of the viewport
        // the rest should be put back into their place in the document
        beforeEach(() => {

          const windowHeight = 460;

          function makeStickysBiggerThanWindow () {

            // make the radios too big to fit in the viewport
            const fields = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
              .map(field => {
                return {
                  label: field,
                  value: field.toLowerCase(),
                  checked: false
                }
              });

            radios.querySelector('fieldset').insertAdjacentHTML('beforeend', helpers.getRadios(fields, 'days'));

            radios.offsetHeight = 475;

          };

          function adjustScreenPositions () {

            const radiosBottom = getScreenItemBottomPosition(radios);

            screenMock.window.setHeightTo(windowHeight);

            // formFooter top should be at the radios bottom
            formFooter.offsetTop = radiosBottom;

            // footer top should be at formFooter's bottom
            footer.offsetTop = getScreenItemBottomPosition(formFooter);

          };

          makeStickysBiggerThanWindow();
          adjustScreenPositions();

          screenMock.scrollTo(inputForm.offsetTop + 10);

          window.GOVUK.stickAtTopWhenScrolling.init()

        });

        test("the number of elements in the group that are stuck should be reduced until it fits into the viewport", () => {

          // when the group is stuck, pageFooter is closest to the viewport edge so should stay sticky
          expect(inputForm.classList.contains('content-fixed-onload')).toBe(true);
          expect(inputForm.classList.contains('content-fixed')).toBe(false);

          // radios are made not sticky
          expect(radios.classList.contains('content-fixed-onload')).toBe(false);
          expect(radios.classList.contains('content-fixed')).toBe(false);

        });

        test("window is scrolled so the sticky elements (stuck and not stuck) appear in sequence", () => {

          // we assume it's useful to start by seeing all the elements in the position they normally sit in the page
          expect(screenMock.window.top).toEqual(inputForm.offsetTop);

        });

      });

    });

  });

  describe("If intending to stick to the bottom", () => {

    let header;
    let content;
    let pageFooter;
    let windowHeight;
    let getFurthestBottomPoint;

    beforeEach(() => {

      document.body.innerHTML = `
        <main role="main" class="govuk-grid-column-three-quarters column-main">
          <a class="govuk-back-link" href="">Back</a>
          <h1 class="heading-large js-header">
            Preview of ‘Content email’
          </h1>
          <div class="wrapper">
            <div class="email-message-body">
              <h2>This is the title</h2>
              <p>This is a paragraph, defined as a block of content where the contents run horizontally across lines.</p>
              <table role="presentation">
                <tbody>
                  <tr>
                    <td>
                      <ul>
                        <li>these</li>
                        <li>are</li>
                        <li>bullet points</li>
                      </ul>
                    </td>
                  </tr>
                </tbody>
              </table>
              <blockquote>
                <p>This block of text is formatted to stand out from the rest</p>
              </blockquote>
              <p>This is a paragraph with a horizontal line underneath.</p>
              <hr>
              <p>This is a paragraph with a horizontal line above.</p>
              <p>This paragraph has a link in it: <a class="govuk-link govuk-link--no-visited-state" href="https://www.gov.uk">https://www.gov.uk</a>.</p>
            </div>
            <div class="page-footer js-stick-at-bottom-when-scrolling">
              <form method="post" action="">
                  <button type="submit" class="govuk-button">Send 1 email </button>
              </form>
            </div>
          </div>
        </main>`;

      heading = document.querySelector('.js-header');
      content = document.querySelector('.email-message-body');
      pageFooter = document.querySelector('.page-footer');

      windowHeight = 940;

      // mock the rendering of all components
      screenMock = new helpers.ScreenMock(jest);
      screenMock.setWindow({
        width: 1990,
        height: windowHeight,
        scrollTop: 0
      });
      screenMock.mockPositionAndDimension('heading', heading, {
        offsetHeight: 75,
        offsetWidth: 727,
        offsetTop: 185
      });
      screenMock.mockPositionAndDimension('content', content, {
        offsetHeight: 900,
        offsetWidth: 727,
        offsetTop: heading.offsetTop + heading.offsetHeight
      });
      screenMock.mockPositionAndDimension('pageFooter', pageFooter, {
        offsetHeight: 50,
        offsetWidth: 727,
        offsetTop: content.offsetTop + content.offsetHeight
      });

      getFurthestBottomPoint = (stickysTotalHeight) => {
        const headingBottom = getScreenItemBottomPosition(heading);

        return headingBottom + PADDING_BEFORE_STOPPING_POINT + stickysTotalHeight;
      };

      // the sticky JS polls for changes to position/dimension so we need to fake setTimeout and setInterval
      jest.useFakeTimers();

    });

    afterEach(() => {

      window.GOVUK.stickAtBottomWhenScrolling.clearEvents();

    });

    test("if bottom of viewport is below bottom of element on load, the element should not be marked as sticky", () => {

      const pageFooterBottom = getScreenItemBottomPosition(pageFooter);

      // scroll so the bottom of the window goes past the bottom of the element
      screenMock.scrollTo((pageFooterBottom - windowHeight) + 10);

      window.GOVUK.stickAtBottomWhenScrolling.init();

      // `.content-fixed-onload` adds the drop-shadow without fading in to show it did not become sticky from user interaction
      expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false);
      expect(pageFooter.classList.contains('content-fixed')).toBe(false);

    });

    test("if the window is 768px or less wide and the bottom of the viewport is above bottom of element on load, the element should not be marked as sticky", () => {

      const pageFooterBottom = getScreenItemBottomPosition(pageFooter);

      screenMock.window.resizeTo({
        height: windowHeight,
        width: 768
      });

      // scroll past top of form
      screenMock.scrollTo(pageFooterBottom - 10);

      window.GOVUK.stickAtTopWhenScrolling.init();

      expect(pageFooter.classList.contains('content-fixed')).toBe(false);
      expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

    });

    describe("if bottom of viewport is above bottom of element on load", () => {

      beforeEach(() => {

        // scroll position defaults to 0 so bottom of window starts at 940px. Element bottom defaults to 1160px.
        window.GOVUK.stickAtBottomWhenScrolling.init();

      });

      test("the element should be marked as already sticky", () => {

        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(true);
        expect(pageFooter.classList.contains('content-fixed')).toBe(false);

      });

      test("a 'shim' element with dimensions matching the sticky element should be added to the document to take up the space it no longer occupies", () => {

        const shim = pageFooter.nextElementSibling;

        expect(shim).not.toBeNull();
        expect(shim.classList.contains('shim')).toBe(true);
        expect(shim.style.height).toEqual(`${pageFooter.offsetHeight}px`);
        expect(shim.style.marginTop).toEqual(''); // 0px would return an empty string
        expect(shim.style.marginBottom).toEqual(''); // 0px would return an empty string

      });

    });

    test("if bottom of viewport is above the furthest point the bottom of the element can go in the scroll area on load, the element should be marked as stopped", () => {

      // change window size so its bottom can go past stopping position
      const windowHeight = 200;
      const furthestBottomPoint = getFurthestBottomPoint(pageFooter.offsetHeight);

      screenMock.window.setHeightTo(windowHeight);

      // scroll the window bottom past the furthest point
      screenMock.scrollTo((furthestBottomPoint - windowHeight) - 10);

      window.GOVUK.stickAtBottomWhenScrolling.init();

      // `.content-fixed-onload` adds the drop-shadow without fading in to show it did not become sticky from user interaction
      expect(pageFooter.classList.contains('content-fixed-onload')).toBe(true);
      expect(pageFooter.classList.contains('content-fixed')).toBe(false);

      // elements are stopped by adding inline styles
      expect(pageFooter.style.position).toEqual('absolute');
      expect(pageFooter.style.top).toEqual(`${furthestBottomPoint - pageFooter.offsetHeight}px`);

    });

    describe("if viewport bottom starts below element bottom", () => {

      let pageFooterBottom;

      beforeEach(() => {

        pageFooterBottom = getScreenItemBottomPosition(pageFooter);

        // change window size so its bottom can go past stopping position
        const windowHeight = 600;

        screenMock.window.setHeightTo(windowHeight);

        // scroll to just below the element
        screenMock.scrollTo((pageFooterBottom - windowHeight) + 10);

        window.GOVUK.stickAtBottomWhenScrolling.init();

      });

      test("if window is scrolled so bottom of it is above the bottom of the element, the element should be marked so it becomes sticky to the user", () => {

        // scroll above bottom of sticky element
        screenMock.scrollTo((pageFooterBottom - windowHeight) - 10);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        // `content-fixed` fades the drop-shadow in to show it became sticky from user interaction
        expect(pageFooter.classList.contains('content-fixed')).toBe(true);
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

      });

      test("if window is scrolled so bottom of it is above the furthest point the bottom of the element can go in the scroll area, the element should be stopped", () => {

        const furthestBottomPoint = getFurthestBottomPoint(pageFooter.offsetHeight);

        // scroll past furthest point
        screenMock.scrollTo((furthestBottomPoint - windowHeight) - 10);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        // `content-fixed` fades the drop-shadow in to show it became sticky from user interaction
        expect(pageFooter.classList.contains('content-fixed')).toBe(true);
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

        // elements are stopped by adding inline styles
        expect(pageFooter.style.position).toEqual('absolute');
        expect(pageFooter.style.top).toEqual(`${furthestBottomPoint - pageFooter.offsetHeight}px`);

      });

      test("if window resizes so bottom is above the bottom of the element, the element should be marked so it becomes sticky to the user", () => {

        // resize window so the bottom is 30px above the bottom of the element
        screenMock.window.resizeTo({ height: 560, width: screenMock.window.width });
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a resize

        // `content-fixed` fades the drop-shadow in to show it became sticky from user interaction
        expect(pageFooter.classList.contains('content-fixed')).toBe(true);
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

      });

    });

    describe("if scrollToRevealElement is called with an element", () => {

      let link;
      let linkBottom;

      beforeEach(() => {

        const contentBottom = getScreenItemBottomPosition(content);

        content.insertAdjacentHTML('afterEnd', '<a href="" id="formatting-options">Formatting options</a>');
        link = document.querySelector('#formatting-options');

        screenMock.mockPositionAndDimension('link', link, {
          offsetHeight: 25, // 25px smaller than the sticky
          offsetWidth: 727,
          offsetTop: contentBottom
        });

        linkBottom = getScreenItemBottomPosition(link);

        // move the sticky over the link. It's 50px high so this position will cause it to overlap.
        screenMock.scrollTo((linkBottom - windowHeight) + 5);

        window.GOVUK.stickAtBottomWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();

      });

      test("the window should scroll so the element is revealed", () => {

        // update inputForm position as DOM normally would
        pageFooter.offsetTop = screenMock.window.bottom - pageFooter.offsetHeight;

        let stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });

        // sticky position should overlap link position
        expect(stickyPosition.top).toBeLessThanOrEqual(link.offsetTop);
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(linkBottom);

        window.GOVUK.stickAtBottomWhenScrolling.scrollToRevealElement(link)

        stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });

        // the top of the sticky element should be at the bottom of the link
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, (linkBottom + pageFooter.offsetHeight) - windowHeight]);

      });

    });

    describe("if viewport bottom starts above element bottom", () => {

      let pageFooterBottom;
      let pageFooterShim;

      beforeEach(() => {

        // scroll position defaults to 0 so bottom of window starts at 940px. Element bottom defaults to 1160px so will be sticky on load.
        pageFooterBottom = getScreenItemBottomPosition(pageFooter);

        // shim will be inserted, inheriting space in the page from pageFooter so store this data
        const pageFooterData = {
          offsetHeight: pageFooter.offsetHeight,
          offsetWidth: pageFooter.offsetWidth,
          offsetTop: pageFooter.offsetTop
        };

        window.GOVUK.stickAtBottomWhenScrolling.init();

        // add mock for shim
        pageFooterShim = document.querySelector('.shim');
        screenMock.mockPositionAndDimension('pageFooterShim', pageFooterShim, pageFooterData);

      });

      test("if window is scrolled so bottom of it is below the bottom of the element, the element should be made not sticky", () => {

        // scroll so bottom of window is below bottom of element
        screenMock.scrollTo((pageFooterBottom - windowHeight) + 10);
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a scroll

        expect(pageFooter.classList.contains('content-fixed')).toBe(false);
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false); // check the class for onload isn't applied

      });

      test("if window resizes so bottom is below the bottom of the element, the element should be made not sticky", () => {

        // resize window so the bottom is 30px above the bottom of the element
        screenMock.window.resizeTo({ height: pageFooterBottom + 10, width: screenMock.window.width });
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a resize

        expect(pageFooter.classList.contains('content-fixed')).toBe(false);
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(false);

      });

      test("if window resizes so bottom is above the furthest point the bottom of the element can go in the scroll area, the element should be stopped", () => {

        const furthestBottomPoint = getFurthestBottomPoint(pageFooter.offsetHeight);

        // resize window so the bottom is above the furthest point
        screenMock.window.resizeTo({ height: furthestBottomPoint - 10, width: screenMock.window.width });
        jest.advanceTimersByTime(60); // fake advance of time to something similar to that for a resize

        expect(pageFooter.classList.contains('content-fixed')).toBe(false); // applied if made sticky after page load
        expect(pageFooter.classList.contains('content-fixed-onload')).toBe(true); // check the class for onload isn't applied

        // elements are stopped by adding inline styles
        expect(pageFooter.style.position).toEqual('absolute');
        expect(pageFooter.style.top).toEqual(`${furthestBottomPoint - pageFooter.offsetHeight}px`);

      });

    });

    describe("if element is made sticky and another element underneath it is focused", () => {

      let checkbox;
      let checkboxBottom;

      beforeEach(() => {

        const contentBottom = getScreenItemBottomPosition(content);

        content.insertAdjacentHTML('afterEnd', '<input type="checkbox" name="confirm" value="yes" />');
        checkbox = document.querySelector('input[type=checkbox]');

        screenMock.mockPositionAndDimension('checkbox', checkbox, {
          offsetHeight: 40, // 10px smaller than the sticky
          offsetWidth: 727,
          offsetTop: contentBottom
        });

        checkboxBottom = getScreenItemBottomPosition(checkbox);

        // move the sticky over the checkbox. It's 50px high so this position will cause it to overlap.
        screenMock.scrollTo((checkboxBottom - windowHeight) + 5);

        window.GOVUK.stickAtBottomWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();

      });

      test("the window should scroll so the focused element is revealed", () => {

        // update inputForm position as DOM normally would
        pageFooter.offsetTop = screenMock.window.bottom - pageFooter.offsetHeight;

        let stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });

        // sticky position should overlap checkbox position
        expect(stickyPosition.top).toBeLessThanOrEqual(checkbox.offsetTop);
        expect(stickyPosition.bottom).toBeGreaterThanOrEqual(checkboxBottom);

        // the sticky element (page footer) is 50 high so should cover the last of the radios if the bottom edge of the viewport is at its bottom
        checkbox.focus();

        stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });

        // the top of the sticky element should be at the bottom of the checkbox
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, (checkboxBottom + pageFooter.offsetHeight) - windowHeight]);

      });

    });

    describe("if element is made sticky and overlaps a textarea", () => {

      let textarea;
      let textareaBottom;
      let caretCoordinates;
      let caretCoordinatesMock;

      beforeEach(() => {

        const contentBottom = getScreenItemBottomPosition(content);

        content.insertAdjacentHTML('afterEnd', '<textarea name="notes"></textarea>');
        textarea = document.querySelector('textarea');

        // line height: 30px, text height: 19px, 10 lines.
        screenMock.mockPositionAndDimension('textarea', textarea, {
          offsetHeight: 300,
          offsetWidth: 727,
          offsetTop: contentBottom
        });

        textareaBottom = getScreenItemBottomPosition(textarea);

        // start caret on the last line
        caretCoordinates = new CaretCoordinates();
        caretCoordinates.moveToLine(10);
        caretCoordinatesMock = jest.fn(() => caretCoordinates);
        window.getCaretCoordinates = caretCoordinatesMock;

        // move the sticky so it overlaps the bottom 50px of the textarea.
        screenMock.scrollTo(textareaBottom - windowHeight);

        // update content position as DOM normally would
        pageFooter.offsetTop = screenMock.window.bottom - pageFooter.offsetHeight;

        window.GOVUK.stickAtBottomWhenScrolling.init();

      });

      afterEach(() => {

        screenMock.window.spies.window.scrollTo.mockClear();
        caretCoordinatesMock.mockClear();

      });

      test("if the textarea receives focus while its caret is underneath, the window should scroll to reveal the caret", () => {

        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // sticky position should overlap caret position
        expect(stickyPosition.top).toBeLessThan(caretPosition.bottom);

        textarea.focus();

        // the top of the sticky element should be at the bottom of the caret
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, caretPosition.bottom - (windowHeight - stickyPosition.height)]);

      });

      test("if the caret is moved so it isn't underneath the sticky element, the window shouldn't scroll", () => {

        // start caret on 8th line which isn't under the sticky element.
        caretCoordinates.moveToLine(8);

        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // the sticky element should be below the caret
        expect(stickyPosition.top).toBeGreaterThan(caretPosition.bottom);

        textarea.focus();

        // no scrolling should have happened
        expect(screenMock.window.spies.window.scrollTo.mock.calls.length).toEqual(0);

      });

      test("if the caret is moved to be underneath the sticky element, the window should scroll to reveal the caret", () => {

        // start caret on 8th line which isn't under the sticky element.
        caretCoordinates.moveToLine(8);

        // make sure the textarea has focus
        textarea.focus();

        // move the caret underneath the sticky element
        caretCoordinates.moveToLine(9);

        const stickyPosition = getStickyGroupPosition(screenMock, { stickyEls: [pageFooter], edge: 'bottom' });
        const caretPosition = getCaretPosition(caretCoordinates, textarea);

        // sticky position should overlap caret position
        expect(stickyPosition.top).toBeLessThan(caretPosition.bottom);

        // simulate a press of the down arrow
        helpers.triggerEvent(textarea, 'keyup', { interface: window.KeyboardEvent });

        // the top of the sticky element should be at the bottom of the caret
        expect(screenMock.window.spies.window.scrollTo.mock.calls[0]).toEqual([0, caretPosition.bottom - (windowHeight - stickyPosition.height)]);

      });

    });

    describe("if mode is set to 'dialog' and multiple sticky elements have the same scroll area", () => {

      let radios;

      beforeEach(() => {

        const contentBottom = getScreenItemBottomPosition(content);

        // set mode to 'dialog' so sticky elements are treated as one item
        window.GOVUK.stickAtBottomWhenScrolling.setMode('dialog')

        // add another sticky element before the form footer
        radios = helpers.getRadioGroup({
          cssClasses: ['js-stick-at-bottom-when-scrolling'],
          name: 'choose-send-time',
          label: 'Choose send time',
          fields: [
            {
              label: 'Now',
              value: 'now',
              checked: true
            },
            {
              label: 'Tomorrow',
              value: 'tomorrow',
              checked: false
            },
            {
              label: 'Friday',
              value: 'friday',
              checked: false
            }
          ]
        });

        pageFooter.parentNode.insertBefore(radios, pageFooter);
        screenMock.mockPositionAndDimension('radios', radios, {
          offsetHeight: 175,
          offsetWidth: 727,
          offsetTop: contentBottom
        });
        const radiosBottom = getScreenItemBottomPosition(radios);

        // adjust other screen items

        // pageFooter top should be at the radios bottom
        pageFooter.offsetTop = radiosBottom;

      });

      afterEach(() => {

        window.GOVUK.stickAtBottomWhenScrolling.setMode('default');

      });

      describe("if window bottom is above the bottom of the lowest element on load", () => {

        let pageFooterBottom;

        beforeEach(() => {

          pageFooterBottom = getScreenItemBottomPosition(pageFooter);

          // scroll to just above the element
          screenMock.scrollTo((pageFooterBottom - windowHeight) - 10);

          window.GOVUK.stickAtBottomWhenScrolling.init();

        });

        test("both should be marked as already sticky", () => {

          expect(pageFooter.classList.contains('content-fixed-onload')).toBe(true);
          expect(pageFooter.classList.contains('content-fixed')).toBe(false);

        });

        test("the highest element should have the drop-shadow", () => {

          expect(radios.classList.contains('content-fixed__bottom')).toBe(true);

        });

        test("they should be stacked from the bottom edge of the viewport in the order they appear in the document", () => {

          expect(radios.style.bottom).toEqual(`${pageFooter.offsetHeight - PADDING_BETWEEN_STICKYS}px`);

        });

      });

      describe("if window bottom is above the furthest point the lowest element can go on load", () => {

        let headingBottom;

        beforeEach(() => {

          const dialogHeight = (pageFooter.offsetHeight + radios.offsetHeight) - PADDING_BETWEEN_STICKYS;
          const furthestBottomPoint = getFurthestBottomPoint(dialogHeight);

          // change window size so its bottom can go past stopping position
          const windowHeight = 200;

          headingBottom = getScreenItemBottomPosition(heading);

          screenMock.window.setHeightTo(windowHeight);

          screenMock.scrollTo((furthestBottomPoint - windowHeight) - 10)

          window.GOVUK.stickAtBottomWhenScrolling.init();

        });

        test("both should be stopped so the top of their stack is at the furthest point", () => {

          expect(radios.style.position).toEqual('absolute');
          expect(pageFooter.style.position).toEqual('absolute');
          expect(radios.style.top).toEqual(`${headingBottom + PADDING_BEFORE_STOPPING_POINT}px`);
          expect(pageFooter.style.top).toEqual(`${headingBottom + PADDING_BEFORE_STOPPING_POINT + (radios.offsetHeight - PADDING_BETWEEN_STICKYS)}px`);

        });

      });

      describe("if the group of sticky elements is taller than the window when stuck together", () => {

        let windowHeight;
        let pageFooterBottom;

        // the sticky behaviour should stick as many elements as possible to the bottom of the viewport
        // the rest should be put back into their place in the document
        beforeEach(() => {

          windowHeight = 460;

          function makeStickysBiggerThanWindow () {

            // make the radios too big to fit in the viewport
            const fields = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
              .map(field => {
                return {
                  label: field,
                  value: field.toLowerCase(),
                  checked: false
                }
              });

            radios.querySelector('fieldset').insertAdjacentHTML('beforeend', helpers.getRadios(fields, 'days'));

            radios.offsetHeight = 475;

          };

          function adjustScreenPositions () {

            const radiosBottom = getScreenItemBottomPosition(radios);

            screenMock.window.setHeightTo(windowHeight);

            // formFooter top should be at the radios bottom
            pageFooter.offsetTop = radiosBottom;

          };

          makeStickysBiggerThanWindow();
          adjustScreenPositions();

          pageFooterBottom = getScreenItemBottomPosition(pageFooter);

          screenMock.scrollTo((pageFooterBottom - windowHeight) - 10);

          window.GOVUK.stickAtBottomWhenScrolling.init()

        });

        test("the number of elements in the group that are stuck should be reduced until it fits into the viewport", () => {

          // when the group is stuck, pageFooter is closest to the viewport edge so should stay sticky
          expect(pageFooter.classList.contains('content-fixed-onload')).toBe(true);
          expect(pageFooter.classList.contains('content-fixed')).toBe(false);

          // radios are made not sticky
          expect(radios.classList.contains('content-fixed-onload')).toBe(false);
          expect(radios.classList.contains('content-fixed')).toBe(false);

        });

        test("window is scrolled so the sticky elements (stuck and not stuck) appear in sequence", () => {

          // we assume it's useful to start by seeing all the elements in the position they normally sit in the page
          expect(screenMock.window.top).toEqual(pageFooterBottom - windowHeight);

        });

      });

    });

  });

});
