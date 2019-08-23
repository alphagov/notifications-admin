const helpers = require('./support/helpers');

beforeAll(() => {
  // TODO: remove this when tests for sticky JS are written
  require('../../app/assets/javascripts/stick-to-window-when-scrolling.js');

  require('../../app/assets/javascripts/fullscreenTable.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('FullscreenTable', () => {
  let windowMock;
  let container;
  let tableFrame;
  let table;
  let numberColumnFrame;

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

    windowMock = new helpers.WindowMock(jest);

    // set up DOM
    document.body.innerHTML =
      `<main>
        <div class="fullscreen-content" data-module="fullscreen-table">
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

  });

  describe("when it loads", () => {

    test("it fixes the number column for each row without changing the semantics", () => {

      // start module
      window.GOVUK.modules.start();

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

      expect(tableFrame).not.toBeNull();
      expect(numberColumnFrame).not.toBeNull();
      expect(numberColumnFrame.getAttribute('role')).toEqual('presentation');

    });

    test("it calls the sticky JS to update any cached dimensions", () => {

      const stickyJSSpy = jest.spyOn(window.GOVUK.stickAtBottomWhenScrolling, 'recalculate');

      // start module
      window.GOVUK.modules.start();

      expect(stickyJSSpy.mock.calls.length).toBe(1);

      stickyJSSpy.mockClear();

    });

  });

  describe("the height of the table should fit the vertical space available to it", () => {

    let containerBoundingClientRectSpy;

    beforeEach(() => {

      // set the height and offset of the window and table container from the top of the document
      // so just the top 268px of it appears on-screen
      windowMock.setHeightTo(768);
      container.setAttribute('style', 'height: 1000px');
      containerBoundingClientRectSpy = jest.spyOn(container, 'getBoundingClientRect')
      containerBoundingClientRectSpy.mockImplementation(() => { return { top: 500 } });

      // start module
      window.GOVUK.modules.start();

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

    });

    afterEach(() => {

      windowMock.reset();
      containerBoundingClientRectSpy.mockClear();

    });

    test("when the page has loaded", () => {

      // the frames should crop to the top 268px of the table that is visible
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('268px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('268px');

    });

    test("when the page has scrolled", () => {

      // scroll the window so the table fills the height of the window (768px)
      windowMock.scrollTo(500);

      // the frames should crop to the window height
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('768px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('768px');

    });

    test("when the page has resized", () => {

      // resize the window by 232px (from 768px to 1000px)
      windowMock.resizeTo({ height: 1000, width: 1024 });

      // the frames should crop to the top 500px of the table now visible
      expect(window.getComputedStyle(tableFrame)['height']).toEqual('500px');
      expect(window.getComputedStyle(numberColumnFrame)['height']).toEqual('500px');

    });

  });

  describe("the width of the table should fit the horizontal space available to it", () => {
    let rowNumberColumnCell;

    beforeEach(() => {

      rowNumberColumnCell = container.querySelector('.table-field-index');

      // set main content column width (used as module as gauge for table width)
      windowMock.setWidthTo(1024);
      document.querySelector('main').setAttribute('style', 'width: 742px');

      // set total width of column for row numbers in table to 40px
      rowNumberColumnCell.setAttribute('style', 'width: 40px');

      // start module
      window.GOVUK.modules.start();

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');

    });

    afterEach(() => {

      windowMock.reset();

    });

    test("when the page has loaded", () => {

      // table should set its width to be that of `<main>`, minus margin-left for the row numbers column
      expect(window.getComputedStyle(tableFrame)['width']).toEqual('702px'); // width of content column - numbers column
      expect(window.getComputedStyle(tableFrame)['margin-left']).toEqual('40px'); // width of numbers column

      // table for number column has 4px extra to allow space for drop shadow
      expect(window.getComputedStyle(numberColumnFrame)['width']).toEqual('44px');

    });

    test("when the page has resized", () => {

      // resize window and content column
      document.querySelector('main').setAttribute('style', 'width: 720px');
      windowMock.resizeTo({ height: 768, width: 960 });

      // table should set its width to be that of `<main>`, minus margin-left for the row numbers column
      expect(window.getComputedStyle(tableFrame)['width']).toEqual('680px'); // width of content column - numbers column
      expect(window.getComputedStyle(tableFrame)['margin-left']).toEqual('40px'); // width of numbers column

      // table for number column has 4px extra to allow space for drop shadow
      expect(window.getComputedStyle(numberColumnFrame)['width']).toEqual('44px');

    });

  });

  describe("when the table scrolls horizontally", () => {
    let rightEdgeShadow;

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      tableFrame = document.querySelector('.fullscreen-scrollable-table');
      table = tableFrame.querySelector('table');
      numberColumnFrame = document.querySelector('.fullscreen-fixed-table');
      rightEdgeShadow = container.querySelector('.fullscreen-right-shadow');

      tableFrame.setAttribute('style', 'width: 742px');
      table.setAttribute('style', 'width: 1000px');

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

});
