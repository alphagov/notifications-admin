const helpers = require('./support/helpers');

beforeAll(() => {
  // set up jQuery
  window.jQuery = require('jquery');
  $ = window.jQuery;

  // load module code
  require('govuk_frontend_toolkit/javascripts/govuk/modules.js');
  require('../../app/assets/javascripts/collapsibleCheckboxes.js');
});

afterAll(() => {
  window.jQuery = null;
  $ = null;

  delete window.GOVUK;
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

    test("adds a heading before the selected fieldset", () => {

      const heading = helpers.element(fieldset).getPreviousSibling(
        el => (el.nodeName === 'h2') && (el.hasClass('heading-small'))
      );

      expect(heading).not.toBeNull();

    });

    test("adds the right content and classes to the summary", () => {

      const summary = formGroup.querySelector('.selection-summary');

      expect(summary.querySelector('p')).not.toBeNull();
      expect(summary.querySelector('p .selection-summary__text')).not.toBeNull();
      debugger;
      expect(summary.querySelector('p .selection-summary__text').classList.contains('selection-summary__text--folders')).toBe(true);

    });

    test("the legend of the fieldset is visually hidden", () => {

      const legend = helpers.element(fieldset.querySelector('legend'));

      expect(legend.hasClass('visuallyhidden')).toBe(true);

    });

    test("has a change button", () => {

      const changeButton = document.querySelector('.selection-summary .button');

      expect(changeButton).not.toBeNull();
      expect(changeButton.textContent).toEqual('Change Folders this team member can see');

    });

    test("has a 'Done' button", () => {

      const nextEl = fieldset.querySelector('.button');

      expect(helpers.element(nextEl).nodeName).toEqual('button');

    });

    test("has the correct aria attributes on both buttons", () => {

      const changeButton = document.querySelector('.selection-summary .button');
      const doneButton = fieldset.querySelector('.button');

      // check change button
      expect(helpers.element(changeButton).hasAttributesSetTo({
        'aria-controls': fieldset.getAttribute('id'),
        'aria-expanded': 'false'
      })).toBe(true);

      // check done button
      expect(helpers.element(doneButton).hasAttributesSetTo({
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
    expect(summaryText.textContent).toEqual("No folders (only templates outside a folder)");

  });

  test('has the right summary text when started with some checkboxes selected', () => {

    // select the first 3 checkboxes
    checkboxes.forEach((el, idx) => {
      if ([0,1,2].includes(idx)) { el.setAttribute('checked', ''); }
    });

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent).toEqual("3 of 10 folders");

  });

  test('has the right summary text when started with all checkboxes selected', () => {

    // select all the checkboxes
    checkboxes.forEach(el => el.setAttribute('checked', ''));

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent).toEqual("All folders");

  });

  test("the summary doesn't have a folder icon if fields aren't called 'folder'", () => {
    
    formGroup.dataset.fieldLabel = 'team member';

    // start module
    window.GOVUK.modules.start();

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.classList.contains('.selection-summary__text-label')).toBe(false);

  });

  describe("when 'change' is clicked", () => {

    let changeButton;
    let doneButton;

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      doneButton = fieldset.querySelector('.button');
      changeButton = document.querySelector('.selection-summary .button');

      helpers.triggerEvent(changeButton, 'click');

    });

    test("it shows the checkboxes", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(false);

    });
    test("it focuses the fieldset", () => {

      expect(document.activeElement).toBe(fieldset);

    });
    test("it uses ARIA to mark the checkboxes as expanded", () => {

      expect(changeButton.getAttribute('aria-expanded')).toEqual('true');
      expect(doneButton.getAttribute('aria-expanded')).toEqual('true');

    });
  });

  describe("when 'done' is clicked", () => {

    let changeButton;
    let doneButton;

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      doneButton = fieldset.querySelector('.button');
      changeButton = document.querySelector('.selection-summary .button');

      // show the checkboxes
      helpers.triggerEvent(changeButton, 'click');

      // click the done button
      helpers.triggerEvent(doneButton, 'click');

    });

    test("it hides the checkboxes", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(true);

    });

    test("it focuses the summary text", () => {

      expect(document.activeElement).toBe(document.querySelector('.selection-summary__text'));

    });

    test("it uses ARIA to mark the checkboxes as collapsed", () => {

      expect(changeButton.getAttribute('aria-expanded')).toEqual('false');
      expect(doneButton.getAttribute('aria-expanded')).toEqual('false');

    });
  });

  describe("when the selection changes", () => {

    const showCheckboxes = () => {
      changeButton = document.querySelector('.selection-summary .button');
      helpers.triggerEvent(changeButton, 'click');
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

    let changeButton;

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

        expect(summaryText.textContent).toEqual("No folders (only templates outside a folder)");

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

        expect(summaryText.textContent).toEqual("No team members");

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

        expect(summaryText.textContent).toEqual("9 of 10 folders");

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

        expect(summaryText.textContent).toEqual("9 of 10 team members");

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

        expect(summaryText.textContent).toEqual("All folders");

      });

      test("if fields are called 'team member'", () => {

        formGroup.dataset.fieldLabel = 'team member';

        checkAllCheckboxesButTheLast();

        // start module
        window.GOVUK.modules.start();

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent).toEqual("All team members");

      });

    });

  });

});
