import FullscreenTable from '../../app/assets/javascripts/esm/fullscreen-table.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers';


describe('FullscreenTable', () => {
  let screenMock;
  let container;
  let caption;
  let tableFrame;
  let table;
  let numberColumnFrame;
  let fixedRowHeaders;

  beforeEach(() => {

    const tableHeadings = () => {
      let result = '';
      const headings = ['1', 'name', 'email address', 'age', 'building number', 'address line 1', 'address line 2', 'postcode'];

      headings.forEach((heading, idx) => {
        if (idx === 0) {
          result += `<th scope="col" class="table-field-heading-first">
                        <span class="visually-hidden">Row in file</span><span aria-hidden="true" class="table-field-invisible-error">${heading}</span>
                      </th>`;
        } else {
          result += `<th scope="col" class="table-field-heading">
                      ${heading}
                      </th>`;
        }
      });

      return result;
    }

    const rowCells = (cells) => {
      let result = '';

      Object.keys(cells).forEach((key, idx) => {
        if (idx === 0) {
          result += `<td class="table-field-index">
                      <span class="table-field-error">
                        ${key}
                      </span>
                    </td>`;
        } else {
          result += `<td class="table-field-left-aligned ">
                      <div class="table-field-status-default">
                        ${key}
                      </div>
                    </td>`;
        }
      });

      return result;
    };

    const tableRows = () => {
      let result = '';

      const rows = [
        ['John Logie Baird', 'johnlbaird@gmail.com', '37', '22', 'Frith Street', 'Soho, London', 'W1D 4RF'],
        ['Guglielmo Marconi', 'gmarconi@hotmail.com', '21', 'Pontecchio Marconi', 'Via Celestini 1', 'Bologna', ''],
        ['Louis Braille', 'louisbraille@yahoo.co.uk', '', '56', 'Boulevard des Invalides', 'Paris', '75007'],
        ['Ray Tomlinson', 'hedy.lamarr@msn.com', '25', '870', '870 Winter Street', 'Waltham', 'MA 02451']
      ];

      rows.forEach(row => {
        result += `<tr class="table-row">${rowCells(row)}</tr>`;
      });

      return result;

    }

    screenMock = new helpers.ScreenMock(jest);
    screenMock.setWindow({
      width: 1990,
      height: 940,
      scrollTop: 0
    });

    window.GOVUK.stickAtBottomWhenScrolling = {
      recalculate: jest.fn(() => {})
    };

    // set up DOM
    document.body.classList.add('govuk-frontend-supported')
    document.body.innerHTML =
      `<main>
        <div class="fullscreen-content" data-notify-module="fullscreen-table">
          <table class="table table-font-xsmall">
            <caption class="heading-medium table-heading visuallyhidden">
              people.csv
            </caption>
            <thead class="table-field-headings-visible">
              <tr>
                ${tableHeadings()}
              </tr>
            </thead>
            <tbody>
              ${tableRows()}
            </tbody>
          </table>
        </div>
       </main>`;

    container = document.querySelector('.fullscreen-content');

  });

  afterEach(() => {
    document.body.innerHTML = '';
    screenMock.reset();
    window.GOVUK.stickAtBottomWhenScrolling.recalculate.mockClear();
    jest.restoreAllMocks();

  });

  describe("when it loads", () => {

    test("it fixes the number column for each row without changing the semantics", () => {

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

      expect(tableFrame).not.toBeNull();
      expect(numberColumnFrame).not.toBeNull();
      expect(numberColumnFrame.getAttribute('aria-hidden')).toEqual('true');

    });

    test("it calls the sticky JS to update any cached dimensions", () => {

      const stickyJSSpy = jest.spyOn(window.GOVUK.stickAtBottomWhenScrolling, 'recalculate');

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      expect(stickyJSSpy.mock.calls.length).toBe(1);

      stickyJSSpy.mockClear();

    });

    describe("and the scrolling section is wider than its container", () => {

      beforeEach(() => {

        screenMock.mockPositionAndDimension('container', container, {
          'offsetHeight': 500,
          'offsetWidth': 640,
          'offsetTop': 500
        });
        screenMock.mockPositionAndDimension('scrollable-table', container.querySelector('table'), {
          'offsetHeight': 500,
          'offsetWidth': 990,
          'offsetTop': 500
        });

        new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))
      });

      afterEach(() => {
        screenMock.resetPositionAndDimension(['container', 'scrollable-table']);
      });

      test("it should be made focusable and have an accessible name matching the table caption", () => {

        tableFrame = document.querySelector('.fullscreen-scrollable-table');
        caption = tableFrame.querySelector('caption');

        // focusable
        expect(tableFrame.hasAttribute('tabindex')).toBe(true);
        expect(tableFrame.getAttribute('tabindex')).toEqual('0');

        // has a semantic role
        expect(tableFrame.hasAttribute('role')).toBe(true);
        expect(tableFrame.getAttribute('role')).toEqual('region');

        // has an accessible name
        expect(tableFrame.hasAttribute('aria-labelledby')).toBe(true);
        expect(tableFrame.getAttribute('aria-labelledby')).toEqual(caption.getAttribute('id'));

      });

    });

    describe("and the scrolling section is the same width as its container", () => {

      beforeEach(() => {

        screenMock.mockPositionAndDimension('container', container, {
          'offsetHeight': 500,
          'offsetWidth': 640,
          'offsetTop': 500
        });
        screenMock.mockPositionAndDimension('scrollable-table', container.querySelector('table'), {
          'offsetHeight': 500,
          'offsetWidth': 640,
          'offsetTop': 500
        });

       new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))
      });

      afterEach(() => {
        screenMock.resetPositionAndDimension(['container', 'scrollable-table']);
        screenMock.reset();
      });

      test("it shouldn't be made focusable or have an accessible name", () => {

        tableFrame = document.querySelector('.fullscreen-scrollable-table');

        // isn't focusable
        expect(tableFrame.hasAttribute('tabindex')).toBe(false);

        // has no semantic role
        expect(tableFrame.hasAttribute('role')).toBe(false);

        // has no accessible name
        expect(tableFrame.hasAttribute('aria-labelledby')).toBe(false);

      });

    });

    test("the section providing the fixed row headers is not focusable and is hidden from assistive tech'", () => {

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      fixedRowHeaders = document.querySelector('.fullscreen-fixed-table');

      expect(fixedRowHeaders.hasAttribute('role')).toBe(false);
      expect(fixedRowHeaders.hasAttribute('aria-labelledby')).toBe(false);
      expect(fixedRowHeaders.hasAttribute('tabindex')).toBe(false);
      expect(fixedRowHeaders.hasAttribute('aria-hidden')).toBe(true);
      expect(fixedRowHeaders.getAttribute('aria-hidden')).toEqual('true');

    });

  });

  describe("the height of the table should fit the vertical space available to it", () => {

    beforeEach(() => {

      // set the height and offset of the window and table container from the top of the document
      // so just the top 268px of it appears on-screen
      screenMock.window.setHeightTo(768);
      screenMock.mockPositionAndDimension('container', container, {
        'offsetHeight': 1000,
        'offsetWidth': 641,
        'offsetTop': 500
      });

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

    });

    afterEach(() => {

      screenMock.resetPositionAndDimension(['container']);
      screenMock.reset();

    });

    test("when the page has loaded", () => {

      // the frames should crop to the top 268px of the table that is visible
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('268px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('268px');

    });

    test("when the page has scrolled", () => {

      // scroll the window so the table fills the height of the window (768px)
      screenMock.window.scrollTo(500);

      // the frames should crop to the window height
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('768px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('768px');

    });

    test("when the page has resized", () => {

      // resize the window by 232px (from 768px to 1000px)
      screenMock.window.resizeTo({ height: 1000, width: 1024 });

      // the frames should crop to the top 500px of the table now visible
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('500px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('500px');

    });

  });

  describe("the width of the table should fit the horizontal space available to it", () => {

    beforeEach(() => {

      // set main content column width (used by module as gauge for table width)
      screenMock.window.setWidthTo(1024);

      screenMock.mockPositionAndDimension('main-element', 'main', {
        'offsetHeight': 500,
        'offsetWidth': 712,
        'offsetTop': 0
      });
      

      // set total width of column for row numbers in table to 40px
      screenMock.mockPositionAndDimension(
        'fixed-table-first-col-header',
        '.fullscreen-fixed-table .table-field-heading-first',
        {
          'offsetHeight': 50,
          'offsetWidth': 40,
          'offsetTop': 0
        }
      );

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

    });

    afterEach(() => {
      screenMock.resetPositionAndDimension(['fixed-table-first-col-header','main-element']);
      screenMock.reset();
    });

    test("when the page has loaded", () => {

      // table should set its width to be that of `<main>`
      expect(window.getComputedStyle(tableFrame).width).toEqual('712px');

      // table for number column has 4px extra to allow space for drop shadow
      expect(window.getComputedStyle(numberColumnFrame)['width']).toEqual('44px');

    });

    test("when the page has resized", () => {

      // resize window and content column
      screenMock.mockPositionAndDimension('main-element', 'main', {
        'offsetHeight': 500,
        'offsetWidth': 668,
        'offsetTop': 0
      }, true);
      screenMock.window.resizeTo({ height: 768, width: 960 });

      // table should set its width to be that of `<main>`
      expect(window.getComputedStyle(tableFrame)['width']).toEqual('668px');

      // table for number column has 4px extra to allow space for drop shadow
      expect(window.getComputedStyle(numberColumnFrame)['width']).toEqual('44px');

    });

  });

  // the layout algorithms browsers use can make the first column different between tables so detection and a fix are both requried
  describe('the first column of both the scrollable table and that with fixed row headers should be the same width', () => {

    afterEach(() => {

      screenMock.reset();

    });

    // table dimensions are set when the module starts and on page resizes
    // we can't fake the columns being different when it starts so our test needs to run after a resize
    test('when the page has resized', () => {

      let invisibleScrollableTopLeftCell;
      let fixedTopLeftHeaderCell;

      // set main content column width (used by module as gauge for table width)
      screenMock.window.setWidthTo(1024);
      screenMock.mockPositionAndDimension('main-element', 'main', {
        'offsetHeight': 500,
        'offsetWidth': 712,
        'offsetTop': 0
      });

      // start module
       new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      invisibleScrollableTopLeftCell = document.querySelector('.fullscreen-scrollable-table .table-field-heading-first');
      fixedTopLeftHeaderCell = document.querySelector('.fullscreen-fixed-table .table-field-heading-first');

      screenMock.mockPositionAndDimension(
        'scrollable-table-first-col-header',
        invisibleScrollableTopLeftCell,
        {
          'offsetHeight': 50,
          'offsetWidth': 30,
          'offsetTop': 0
        }
      );

      screenMock.mockPositionAndDimension(
        'fixed-table-first-col-header',
        fixedTopLeftHeaderCell,
        {
          'offsetHeight': 50,
          'offsetWidth': 9,
          'offsetTop': 0
        }
      );

      screenMock.window.resizeTo({ height: 1000, width: 600 });

      expect(window.getComputedStyle(invisibleScrollableTopLeftCell)['width']).toEqual('9px');

    });

  });

  describe("when the table scrolls horizontally", () => {
    let rightEdgeShadow;

    beforeEach(() => {

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      table = tableFrame.querySelector('table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');
      rightEdgeShadow = container.querySelector('.fullscreen-right-shadow');

      screenMock.mockPositionAndDimension('scrollable-table-container', tableFrame, {
        'offsetHeight': 500,
        'offsetWidth': 742,
        'offsetTop': 500
      });

      screenMock.mockPositionAndDimension('scrollable-table-table', table, {
        'offsetHeight': 500,
        'offsetWidth': 1000,
        'offsetTop': 500
      });

    });

    afterEach(() => {
      screenMock.resetPositionAndDimension(['scrollable-table-container', 'scrollable-table-table']);
    });

    test("the right edge of the table scroll area should have a drop-shadow if it isn't scrolled", () => {

      tableFrame.scrollLeft = 0;
      helpers.triggerEvent(tableFrame, 'scroll');

      expect(numberColumnFrame.classList.contains('fullscreen-scrolled-table')).toBe(false);
      expect(rightEdgeShadow.classList.contains('visible')).toBe(true);

    });

    test("the left edge of the table scroll area should have a drop-shadow if the table is scrolled to 100%", () => {

      // scroll to end of table
      tableFrame.scrollLeft = 258;
      helpers.triggerEvent(tableFrame, 'scroll');

      expect(numberColumnFrame.classList.contains('fullscreen-scrolled-table')).toBe(true);
      expect(rightEdgeShadow.classList.contains('visible')).toBe(false);

    });

    test("both edges of the table scroll area should have a drop-shadow if the table is scrolled between 0% and 100%", () => {

      // scroll to middle of table
      tableFrame.scrollLeft = 129;
      helpers.triggerEvent(tableFrame, 'scroll');

      expect(numberColumnFrame.classList.contains('fullscreen-scrolled-table')).toBe(true);
      expect(rightEdgeShadow.classList.contains('visible')).toBe(true);

    });

  });

  describe("when the table is focused", () => {

    beforeEach(() => {

      screenMock.mockPositionAndDimension('container', container, {
        'offsetHeight': 500,
        'offsetWidth': 640,
        'offsetTop': 500
      });

      screenMock.mockPositionAndDimension('scrollable-table', container.querySelector('table'), {
        'offsetHeight': 500,
        'offsetWidth': 990,
        'offsetTop': 500
      });

      // start module
      new FullscreenTable(document.querySelector('[data-notify-module="fullscreen-table"]'))

      tableFrame = container.querySelector('.fullscreen-scrollable-table');
      tableFrame.focus();
    });

     afterEach(() => {
      screenMock.resetPositionAndDimension(['container', 'scrollable-table']);
    });

    test("it should make the parent frame a focus style", () => {

      expect(container.classList.contains('js-focus-style')).toBe(true);

    });

  });

});
