  const helpers = require('./support/helpers');

beforeAll(() => {
  require('../../app/assets/javascripts/addEmailBrandingOptionsForm.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('AddEmailBrandingOptionsForm', () => {

  let addEmailBrandingOptionsForm;
  let formControls;
  let visibleCounter;
  let hiddenCounter;

  beforeEach(() => {

    const htmlFragment = `
      <form method="post" autocomplete="off" data-notify-module="add-email-branding-options-form" novalidate="">
        <div class="brand-pool">
          <div class="govuk-form-group">
            <fieldset class="govuk-fieldset" id="branding_field">
              <legend class="govuk-fieldset__legend govuk-visually-hidden">
                Branding options
              </legend>
              <div class="govuk-checkboxes">
                <div class="govuk-checkboxes__item"><input class="govuk-checkboxes__input" id="branding_field-0" name="branding_field" type="checkbox" value="7f8d0c7f-fe8f-4723-bdce-8a19012bb24b">
                  <label class="govuk-label govuk-checkboxes__label" for="branding_field-0">
                  Branding only
                  </label>
                </div>
              <div class="govuk-checkboxes__item"><input class="govuk-checkboxes__input" id="branding_field-1" name="branding_field" type="checkbox" value="b5e5f5ab-6407-4f35-9b8c-9fb36e2ccd3f">
                <label class="govuk-label govuk-checkboxes__label" for="branding_field-1">
                Branding only with colour
                </label>
              </div>
              <div class="govuk-checkboxes__item"><input class="govuk-checkboxes__input" id="branding_field-2" name="branding_field" type="checkbox" value="23742f8c-0612-4eba-83e6-5bcdd884b0e0">
                <label class="govuk-label govuk-checkboxes__label" for="branding_field-2">
                Branding with banner
                </label>
              </div>
            </div>
          </fieldset>
        </div>
      </div>
      <div class="js-stick-at-bottom-when-scrolling">
        <div class="page-footer">
          <input type="hidden" name="csrf_token" value="ImYxODZjNDJkODcwMmEwZGZjZTA2OWQ2OTM3YmJhM2IxMWUyM2NlNDYi.YxicPg.8an7lw_jl4Q3pfURcMKAV7Ufps8">
          <button type="submit" class="govuk-button page-footer__button">
            Add options
          </button>
        </div>
        <div class="selection-counter govuk-visually-hidden" role="status" aria-live="polite">
          Nothing selected
        </div>
      </div>
    </form>
  `;

    document.body.innerHTML = htmlFragment;

    addEmailBrandingOptionsForm = document.querySelector('form[data-notify-module=add-email-branding-options-form]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  function getEmailBrandingOptionsCheckboxes () {
    return addEmailBrandingOptionsForm.querySelectorAll('input[type=checkbox]');
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

      formControls = addEmailBrandingOptionsForm.querySelector('.js-stick-at-bottom-when-scrolling');
      visibleCounter = getVisibleCounter();

    });

    test("the counter should be showing", () => {

      expect(visibleCounter).not.toBeNull();

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

        expect(visibleCounter.textContent.trim()).toEqual('Nothing selected');

      });

    });

    describe("When some branding options are selected", () => {

      let EmailBrandingOptionsCheckboxes;

      beforeEach(() => {

        // start module
        window.GOVUK.notifyModules.start();

        EmailBrandingOptionsCheckboxes = getEmailBrandingOptionsCheckboxes();

        formControls = addEmailBrandingOptionsForm.querySelector('.js-stick-at-bottom-when-scrolling');

        helpers.triggerEvent(EmailBrandingOptionsCheckboxes[0], 'click');
        helpers.triggerEvent(EmailBrandingOptionsCheckboxes[2], 'click');

      });

      describe("'Clear selection' link", () => {

        let clearLink;

        beforeEach(() => {

          clearLink = formControls.querySelector('.js-cancel');

        });

        test("the link has been added with the right text", () => {

          expect(clearLink).not.toBeNull();
          expect(clearLink.textContent.trim()).toEqual('Clear selection');

        });

        test("clicking the link clears the selection", () => {

          helpers.triggerEvent(clearLink, 'click');

          const checkedCheckboxes = Array.from(EmailBrandingOptionsCheckboxes).filter(checkbox => checkbox.checked);

          expect(checkedCheckboxes.length === 0).toBe(true);

        });

        test("clicking the link moves focus to first checkbox", () => {

          helpers.triggerEvent(clearLink, 'click');

          const firstCheckbox = EmailBrandingOptionsCheckboxes[0];

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

          expect(visibleCounterText).toEqual('2 options selected');

        });

      });

   });
  });
})
