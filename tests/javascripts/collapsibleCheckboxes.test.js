const helpers = require('./support/helpers');

beforeAll(() => {
  // TODO: remove this when tests for sticky JS are written
  require('../../app/assets/javascripts/stick-to-window-when-scrolling.js');

  require('../../app/assets/javascripts/collapsibleCheckboxes.js');
});

afterAll(() => {
  require('./support/teardown.js');
});


describe('Collapsible fieldset', () => {

  let fieldset;
  let checkboxes;

  beforeEach(() => {
    const _checkboxes = (start, end, descendents) => {
      result = '';

        for (let num = start; num <= end; num++) {
          let id = `folder-permissions-${num}`;

          if (!descendents) { descendents = ''; }

          result += `<li class="multiple-choice">
            <input id="${id}" name="folder_permissions" type="checkbox" value="${id}">
            <label class="block-label" for="{id}">
              Folder 18
            </label>
            ${descendents}
          </li>`;
        }

        return result;
    };

    // set up DOM
    document.body.innerHTML =
      `<div class="form-group" data-module="collapsible-checkboxes" data-field-label="folder">
        <div class="selection-summary"></div>
        <fieldset id="folder_permissions">
          <legend class="form-label heading-small">
            Folders this team member can see
          </legend>
          <div class="checkboxes-nested">
            <ul>
              ${_checkboxes(1, 10)}
            </ul>
          </div>
        </fieldset>
      </div>`;

      formGroup = document.querySelector('.form-group');
      fieldset = formGroup.querySelector('fieldset');
      checkboxesContainer = fieldset.querySelector('.checkboxes-nested');
      checkboxes = checkboxesContainer.querySelectorAll('input[type=checkbox]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe('when started', () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

    });

    afterEach(() => {

      // reset checkboxes to default state
      checkboxes.forEach(el => el.removeAttribute('checked'));

    });

    test("adds the right classes to the group and fieldset", () => {

      expect(formGroup.classList.contains('selection-wrapper')).toBe(true);
      expect(fieldset.classList.contains('selection-content')).toBe(true);

    });

    test("adds a heading before the selected fieldset", () => {

      const heading = helpers.element(fieldset).getPreviousSibling(
        el => (el.nodeName === 'h2') && (el.hasClass('heading-small'))
      );

      expect(heading).not.toBeNull();

    });

    test("adds the right content and classes to the summary", () => {

      const summary = formGroup.querySelector('.selection-summary__text');

      expect(summary).not.toBeNull();
      expect(summary.classList.contains('selection-summary__text--folders')).toBe(true);

    });

    test("the legend of the fieldset is visually hidden", () => {

      const legend = helpers.element(fieldset.querySelector('legend'));

      expect(legend.hasClass('visuallyhidden')).toBe(true);

    });

    test("has a button to expand the fieldset", () => {

      const button = formGroup.querySelector('.button');

      expect(button).not.toBeNull();
      expect(button.textContent.trim()).toEqual('Choose folders');

    });

    test("has the correct aria attributes on the button", () => {

      expect(helpers.element(formGroup.querySelector('.button')).hasAttributesSetTo({
        'aria-controls': fieldset.getAttribute('id'),
        'aria-expanded': 'false'
      })).toBe(true);

    });

    test("hides the checkboxes", () => {

      expect(helpers.element(fieldset).is('hidden')).toEqual(true);

    });

  });

  test('has the right summary text when started with no checkboxes selected', () => {

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    // default state is for none to be selected
    expect(summaryText.textContent.trim()).toEqual("No folders (only templates outside a folder)");

  });

  test('has the right summary text when started with some checkboxes selected', () => {

    // select the first 3 checkboxes
    checkboxes.forEach((el, idx) => {
      if ([0,1,2].includes(idx)) { el.setAttribute('checked', ''); }
    });

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent.trim()).toEqual("3 of 10 folders");

  });

  test('has the right summary text when started with all checkboxes selected', () => {

    // select all the checkboxes
    checkboxes.forEach(el => el.setAttribute('checked', ''));

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent.trim()).toEqual("All folders");

  });

  test("the summary doesn't have a folder icon if fields aren't called 'folder'", () => {

    formGroup.dataset.fieldLabel = 'team member';

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.classList.contains('.selection-summary__text-label')).toBe(false);

  });

  describe("when button is clicked while the fieldset is collapsed", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');

    });

    test("it shows the checkboxes", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(false);

    });

    test("it focuses the fieldset", () => {

      expect(document.activeElement).toBe(fieldset);

    });

    test("it uses ARIA to mark the checkboxes as expanded", () => {

      expect(formGroup.querySelector('.button').getAttribute('aria-expanded')).toEqual('true');

    });

    test("it changes it's text to indicate it's new action", () => {

      expect(formGroup.querySelector('.button').textContent.trim()).toEqual("Done choosing folders");

    });

  });

  describe("when button is clicked when the fieldset is expanded", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      // show the checkboxes
      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');

      // click the button
      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');

    });

    test("it hides the checkboxes", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(true);

    });

    test("it focuses the summary text", () => {

      expect(document.activeElement).toBe(document.querySelector('.selection-summary__text'));

    });

    test("it uses ARIA to mark the checkboxes as collapsed", () => {

      expect(formGroup.querySelector('.button').getAttribute('aria-expanded')).toEqual('false');

    });

    test("it changes it's text to indicate it's new action", () => {

      expect(formGroup.querySelector('.button').textContent.trim()).toEqual("Choose folders");

    });
  });

  describe("the footer (that wraps the button)", () => {

    beforeEach(() => {

      // track calls to sticky JS
      window.GOVUK.stickAtBottomWhenScrolling.recalculate = jest.fn(() => {});

      // start module
      window.GOVUK.modules.start();

      // show the checkboxes
      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');

    });

    test("is made sticky when the fieldset is expanded", () => {

      expect(formGroup.querySelector('.selection-footer').classList.contains('js-stick-at-bottom-when-scrolling')).toBe(true);
      expect(window.GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toBe(1);

    });

    test("has its stickiness removed when the fieldset is collapsed", () => {

      // click the button to collapse the fieldset
      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');

      expect(formGroup.querySelector('.selection-footer').classList.contains('js-stick-at-bottom-when-scrolling')).toBe(false);
      expect(window.GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toBe(2);

    });
  });

  describe("when the selection changes", () => {

    const showCheckboxes = () => {
      helpers.triggerEvent(formGroup.querySelector('.button'), 'click');
    };

    const checkFirstCheckbox = () => {
      checkboxes[0].setAttribute('checked', '');
      checkboxes[0].checked = true;
    };

    const checkAllCheckboxes = () => {
      Array.from(checkboxes).forEach(checkbox => {
        checkbox.setAttribute('checked', '');
        checkbox.checked = true;
      });
    };

    const checkAllCheckboxesButTheLast = () => {
      Array.from(checkboxes).forEach((checkbox, idx) => {
        if (idx > 0) {
          checkbox.setAttribute('checked', '');
          checkbox.checked = true;
        }
      });
    };

    describe("from some to none the summary updates to reflect that", () => {

      test("if fields are called 'folders'", () => {

        formGroup.dataset.fieldLabel = 'folder';

        checkFirstCheckbox();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No folders (only templates outside a folder)");

      });

      test("if fields are called 'team member'", () => {

        formGroup.dataset.fieldLabel = 'team member';

        checkFirstCheckbox();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No team members (only you)");

      });

      test("if fields are called 'arbitrary thing'", () => {

        formGroup.dataset.fieldLabel = 'arbitrary thing';

        checkFirstCheckbox();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No arbitrary things");

      });

    });

    describe("from all to some the summary updates to reflect that", () => {

      test("if fields are called 'folder'", () => {

        formGroup.dataset.fieldLabel = 'folder';

        checkAllCheckboxes();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[1], 'click');

        expect(summaryText.textContent.trim()).toEqual("9 of 10 folders");

      });

      test("if fields are called 'team member'", () => {

        formGroup.dataset.fieldLabel = 'team member';

        checkAllCheckboxes();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[1], 'click');

        expect(summaryText.textContent.trim()).toEqual("9 of 10 team members");

      });

    });

    describe("from some to all the summary updates to reflect that", () => {

      test("if fields are called 'folder'", () => {

        formGroup.dataset.fieldLabel = 'folder';

        checkAllCheckboxesButTheLast();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("All folders");

      });

      test("if fields are called 'team member'", () => {

        formGroup.dataset.fieldLabel = 'team member';

        checkAllCheckboxesButTheLast();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("All team members");

      });

    });

  });

});
