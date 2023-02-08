const helpers = require('./support/helpers');

beforeAll(() => {
  require('../../app/assets/javascripts/liveCheckboxControls.js');
  require('../../app/assets/javascripts/setAuthTypeForm.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('SetAuthTypeForm', () => {

  let setAuthTypeForm;
  let formControls;
  let visibleCounter;
  let hiddenCounter;

  beforeEach(() => {

    const htmlFragment = `
      <form method="post" autocomplete="off" data-notify-module="set-auth-type-form" data-thing-singular="team member" data-thing-plural="team members" novalidate="" class="sticky-scroll-area">
        <div class="govuk-form-group">
          <fieldset class="govuk-fieldset" aria-describedby="users-hint" id="users">
            <legend class="govuk-fieldset__legend govuk-fieldset__legend--l">
              <h1 class="govuk-fieldset__heading">Choose who can sign in using an email link</h1>
            </legend>
            <div id="users-hint" class="govuk-hint">Team members</div>
            <div class="govuk-checkboxes" data-module="govuk-checkboxes">
              <div class="govuk-checkboxes__item">
                <input class="govuk-checkboxes__input" id="users-0" name="users" type="checkbox" value="user-a">
                <label class="govuk-label govuk-checkboxes__label" for="users-0">User A</label>
              </div>
              <div class="govuk-checkboxes__item">
                <input class="govuk-checkboxes__input" id="users-1" name="users"type="checkbox" value="user-b">
                <label class="govuk-label govuk-checkboxes__label" for="users-1">User B</label>
              </div>
              <div class="govuk-checkboxes__item">
                <input class="govuk-checkboxes__input" id="users-2" name="users"type="checkbox" value="user-c">
                <label class="govuk-label govuk-checkboxes__label" for="users-2">User C</label>
              </div>
            </div>
          </fieldset>
        </div>
        <p class="govuk-body">
          If you need to change someone's sign-in method later, go to the team members page.
        </p>
        <div class="js-stick-at-bottom-when-scrolling">
          <div class="page-footer">
            <button class="govuk-button page-footer__button" data-module="govuk-button">Save</button>
          </div>
          <div class="selection-counter govuk-visually-hidden" role="status" aria-live="polite">No team members selected</div>
        </div>
      </form>`;

    document.body.innerHTML = htmlFragment;

    setAuthTypeForm = document.querySelector('form[data-notify-module=set-auth-type-form]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  function getUserCheckboxes () {
    return setAuthTypeForm.querySelectorAll('input[type=checkbox]');
  };

  function getVisibleCounter () {
    return formControls.querySelector('.checkbox-list-selected-counter__count');
  };

  function getHiddenCounter () {
    return formControls.querySelector('[role=status]');
  };

  describe("When the module starts", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.notifyModules.start();

      formControls = setAuthTypeForm.querySelector('.js-stick-at-bottom-when-scrolling');
      visibleCounter = getVisibleCounter();

    });

    test("the counter should be showing", () => {

      expect(visibleCounter).not.toBeNull();

    });

    test("the 'Select all' link should be showing", () => {

      var selectAllLink = formControls.querySelector('.js-action');

      expect(selectAllLink).not.toBeNull();
      expect(selectAllLink.textContent.trim()).toEqual('Select all team members');

    });

    // Our counter needs to be wrapped in an ARIA live region so changes to its content are
    // communicated to assistive tech'.
    // ARIA live regions need to be in the HTML before JS loads.
    // Because of this, we have a counter, in a live region, in the page when it loads, and
    // a duplicate, visible, one in the HTML the module adds to the page.
    // We hide the one in the live region to avoid duplication of it's content.
    describe("Selection counter", () => {

      beforeEach(() => {

        hiddenCounter = getHiddenCounter();

      })

      test("the visible counter should be hidden from assistive tech", () => {

        expect(visibleCounter.getAttribute('aria-hidden')).toEqual("true");

      });

      test("the content of both visible and hidden counters should match", () => {

        expect(visibleCounter.textContent.trim()).toEqual(hiddenCounter.textContent.trim());
      });

      test("the content of the counter should reflect the selection", () => {

        expect(visibleCounter.textContent.trim()).toEqual('No team members selected');

      });

    });

    describe("When some team members are selected", () => {

      let UserCheckboxes;

      beforeEach(() => {

        // start module
        window.GOVUK.notifyModules.start();

        UserCheckboxes = getUserCheckboxes();

        formControls = setAuthTypeForm.querySelector('.js-stick-at-bottom-when-scrolling');

        helpers.triggerEvent(UserCheckboxes[0], 'click');
        helpers.triggerEvent(UserCheckboxes[2], 'click');

      });

      describe("'Clear selection' link", () => {

        let clearLink;

        beforeEach(() => {

          clearLink = formControls.querySelector('.js-action');

        });

        test("the link has been added with the right text", () => {

          expect(clearLink).not.toBeNull();
          expect(clearLink.textContent.trim()).toEqual('Clear selection');

        });

        test("clicking the link clears the selection", () => {

          helpers.triggerEvent(clearLink, 'click');

          const checkedCheckboxes = Array.from(UserCheckboxes).filter(checkbox => checkbox.checked);

          expect(checkedCheckboxes.length === 0).toBe(true);

        });

        test("clicking the link moves focus to first checkbox", () => {

          helpers.triggerEvent(clearLink, 'click');

          const firstCheckbox = UserCheckboxes[0];

          expect(document.activeElement).toBe(firstCheckbox);

        });

      });

      describe("Selection counter", () => {

        let visibleCounterText;
        let hiddenCounterText;

        beforeEach(() => {

          visibleCounterText = getVisibleCounter().textContent.trim();
          hiddenCounterText = getHiddenCounter().textContent.trim();

        });

        test("the content of both visible and hidden counters should match", () => {

          expect(visibleCounterText).toEqual(hiddenCounterText);

        });

        test("the content of the counter should reflect the selection", () => {

          expect(visibleCounterText).toEqual('2 team members selected');

        });

      });

   });
  });
})
