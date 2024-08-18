import CollapsibleCheckboxes from '../../app/assets/javascripts/esm/collapsible-checkboxes.mjs'
import * as helpers from './support/helpers.js'

describe('Collapsible checkboxes', () => {

  const _checkboxes = (start, end) => {
    let result = '';

      for (let num = start; num <= end; num++) {
        let id = `folder-permissions-${num}`;

        result += `<li class="govuk-checkboxes__item">
          <input class="govuk-checkboxes__input" id="${id}" name="folder-permissions" type="checkbox" value="${id}">
          <label class="govuk-label govuk-checkboxes__label" for="${id}">
            Folder ${id}
          </label>
        </li>`;
      }

      return result;
  };
  let wrapper;
  let formGroup;
  let fieldset;
  let checkboxesContainer;
  let checkboxes;

  beforeEach(() => {
    // add class to mimic IRL 
    document.body.classList.add('govuk-frontend-supported')
    // set up DOM
    document.body.innerHTML =
      `<div class="selection-wrapper" data-notify-module="collapsible-checkboxes" data-field-label="folder">
        <div class="govuk-form-group">
          <fieldset class="govuk-fieldset" id="folder_permissions" aria-describedby="users_with_permission-hint">
            <legend class="govuk-fieldset__legend govuk-fieldset__legend--s">
              Folders this team member can see
              <span class="govuk-hint" id="users_with_permission-hint">
                <div class="selection-summary" role="region" aria-live="polite"></div>
              </span>
            </legend>
            <ul class="govuk-checkboxes">
              ${_checkboxes(1, 10)}
            </ul>
          </fieldset>
        </div>
      </div>`;

      wrapper = document.querySelector('.selection-wrapper');
      formGroup = wrapper.querySelector('.govuk-form-group');
      fieldset = formGroup.querySelector('fieldset');
      checkboxesContainer = fieldset.querySelector('.govuk-checkboxes');
      checkboxes = checkboxesContainer.querySelectorAll('input[type=checkbox]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe('when started', () => {

    beforeEach(() => {

      // start module
      new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

    });

    afterEach(() => {

      // reset checkboxes to default state
      checkboxes.forEach(el => el.removeAttribute('checked'));

    });

    test("adds the right classes to the group and fieldset", () => {
      

      expect(fieldset.classList.contains('selection-wrapper')).toBe(true);
      expect(checkboxesContainer.classList.contains('selection-content')).toBe(true);

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

      expect(legend.hasClass('govuk-visually-hidden')).toBe(true);

    });

    test("has a button to expand the checkboxes container", () => {

      const button = formGroup.querySelector('.govuk-button');

      expect(button).not.toBeNull();
      expect(button.textContent.trim()).toEqual('Choose folders this team member can see');

    });

    test("has the correct aria attributes on the button", () => {

      expect(helpers.element(formGroup.querySelector('.govuk-button')).hasAttributesSetTo({
        'aria-expanded': 'false'
      })).toBe(true);

    });

    test("hides the fieldset", () => {

      expect(helpers.element(fieldset).is('hidden')).toEqual(true);

    });

    test("the hint is removed", () => {

      expect(document.querySelector('.govuk-hint')).toBeNull();

    });

    describe("the live region that was inside the hint", () => {
      let childNodesinContainer;
      beforeEach(() => {
        childNodesinContainer = Array.from(document.querySelector('fieldset').parentNode.children)
      })

      test("is moved above the fieldset", () => {

        // as the summary live region is before the toggle button, it's no longer
        // directly before the fieldsset
        // as a proxy we can check direct children on fieldset's parent 
        // and compare indexes in the array. 
        // summary live region's will be lower than fieldset's

        expect(childNodesinContainer.findIndex(({classList}) => classList.contains('selection-summary')) < childNodesinContainer.findIndex(({tagName}) => tagName.toLowerCase() === 'fieldset'))

      });

      test("has an id matching the aria-describedby on the fieldset", () => {

        const fieldsetDescribedby = fieldset.getAttribute('aria-describedby');
        const summaryLiveRegionId = childNodesinContainer.filter(element => element.classList.contains('selection-summary')).map(element => element.id).toString()
    
        expect(summaryLiveRegionId).toEqual(fieldsetDescribedby);

      });

    });

  });

  test('has the right summary text when started with no checkboxes selected', () => {

    // start module
    new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

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
    new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent.trim()).toEqual("3 of 10 folders");

  });

  test('has the right summary text when started with all checkboxes selected', () => {

    // select all the checkboxes
    checkboxes.forEach(el => el.setAttribute('checked', ''));

    // start module
    new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.textContent.trim()).toEqual("All folders");

  });

  test("the summary doesn't have a folder icon if fields aren't called 'folder'", () => {

    wrapper.dataset.fieldLabel = 'team member';

    // start module
    new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

    const summaryText = document.querySelector('.selection-summary__text');

    expect(summaryText.classList.contains('.selection-summary__text-label')).toBe(false);

  });

  describe("when button is clicked while the checkboxes are collapsed", () => {

    beforeEach(() => {

      // start module
      new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

      helpers.triggerEvent(formGroup.querySelector('.govuk-button'), 'click');

    });

    test("it shows the checkboxes (inside the fieldset)", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(false);

    });

    test("it uses ARIA to mark the checkboxes as expanded", () => {

      expect(formGroup.querySelector('.govuk-button').getAttribute('aria-expanded')).toEqual('true');

    });

  });

  describe("when button is clicked when the checkboxes are expanded", () => {

    beforeEach(() => {

      // start module
      new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

      // show the checkboxes
      helpers.triggerEvent(formGroup.querySelector('.govuk-button'), 'click');

      // click the button
      helpers.triggerEvent(formGroup.querySelector('.govuk-button'), 'click');

    });

    test("it hides the checkboxes (inside the fieldset)", () => {

      expect(helpers.element(fieldset).is('hidden')).toBe(true);

    });

    test("it uses ARIA to mark the checkboxes as collapsed", () => {

      expect(formGroup.querySelector('.govuk-button').getAttribute('aria-expanded')).toEqual('false');

    });

    test("it changes it's text to indicate it's new action", () => {

      expect(formGroup.querySelector('.govuk-button').textContent.trim()).toEqual("Choose folders this team member can see");

    });
  });

  describe("when the selection changes", () => {

    const showCheckboxes = () => {
      helpers.triggerEvent(formGroup.querySelector('.govuk-button'), 'click');
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

        wrapper.dataset.fieldLabel = 'folder';

        checkFirstCheckbox();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No folders (only templates outside a folder)");

      });

      test("if fields are called 'team member'", () => {

        wrapper.dataset.fieldLabel = 'team member';

        checkFirstCheckbox();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No team members (only you)");

      });

      test("if fields are called 'arbitrary thing'", () => {

        wrapper.dataset.fieldLabel = 'arbitrary thing';

        checkFirstCheckbox();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("No arbitrary things");

      });

    });

    describe("from all to some the summary updates to reflect that", () => {

      test("if fields are called 'folder'", () => {

        wrapper.dataset.fieldLabel = 'folder';

        checkAllCheckboxes();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[1], 'click');

        expect(summaryText.textContent.trim()).toEqual("9 of 10 folders");

      });

      test("if fields are called 'team member'", () => {

        wrapper.dataset.fieldLabel = 'team member';

        checkAllCheckboxes();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        // click the first checkbox
        helpers.triggerEvent(checkboxes[1], 'click');

        expect(summaryText.textContent.trim()).toEqual("9 of 10 team members");

      });

    });

    describe("from some to all the summary updates to reflect that", () => {

      test("if fields are called 'folder'", () => {

        wrapper.dataset.fieldLabel = 'folder';

        checkAllCheckboxesButTheLast();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("All folders");

      });

      test("if fields are called 'team member'", () => {

        wrapper.dataset.fieldLabel = 'team member';

        checkAllCheckboxesButTheLast();

        // start module
        new CollapsibleCheckboxes(document.querySelector('[data-notify-module="collapsible-checkboxes"]'))

        showCheckboxes();

        const summaryText = document.querySelector('.selection-summary__text');

        helpers.triggerEvent(checkboxes[0], 'click');

        expect(summaryText.textContent.trim()).toEqual("All team members");

      });

    });

  });

});
