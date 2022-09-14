// Before the module starts
//   ✓ the HTML for the module should contain placeholder classes on each part that needs to be sticky (15 ms)
// When the module starts
//   ✓ the default controls and the counter should be showing (38 ms)
//   ✓ should make the current controls sticky (29 ms)
//   Selection counter
//     ✓ the visible counter should be hidden from assistive tech (13 ms)
//     ✓ the content of both visible and hidden counters should match (13 ms)
//
//
// When some templates/folders are selected
//       ✓ the buttons for moving to a new or existing folder are showing (11 ms)
//       ✓ should make the current controls sticky (11 ms)
//       'Clear selection' link
//         ✓ the link has been added with the right text (9 ms)
//         ✓ clicking the link clears the selection (10 ms)
//         ✓ clicking the link puts Focus on  (10 ms)
//       Selection counter
//         ✓ the content of both visible and hidden counters should match (9 ms)
//         ✓ the content of the counter should reflect the selection (8 ms)
//



beforeAll(() => {
  require('../../app/assets/javascripts/addEmailBrandingOptionsForm.js');

  // plug JSDOM's lack of support for window.scrollTo
  window.scrollTo = () => {};
});

afterAll(() => {
  require('./support/teardown.js');

  // tidy up
  delete window.scrollTo;
});

describe('TemplateFolderForm', () => {

  let addEmailBrandingOptionsForm;
  let formControls;
  let visibleCounter;
  let hiddenCounter;

  beforeEach(() => {

    const htmlFragment = `
      <form method="post" autocomplete="off" data-module="add-email-branding-options-form" novalidate="">
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

    addEmailBrandingOptionsForm = document.querySelector('form[data-module=add-email-branding-options-form]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  function getEmailBrandingOptionsCheckboxes () {
    return addEmailBrandingOptionsForm.querySelectorAll('input[type=checkbox]');
  };

  function getVisibleCounter () {
    return formControls.querySelector('.template-list-selected-counter__count');
  };

  function getHiddenCounter () {
    return formControls.querySelector('[role=status]');
  };

  describe("When the module starts", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

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
    });

//     describe("When some branding options are selected", () => {
//
//       let EmailBrandingOptionsCheckboxes;
//
//       beforeEach(() => {
//
//         // start module
//         window.GOVUK.modules.start();
//
//         EmailBrandingOptionsCheckboxes = getEmailBrandingOptionsCheckboxes();
//
//         formControls = templateFolderForm.querySelector('.brand-pool');
//
//         helpers.triggerEvent(EmailBrandingOptionsCheckboxes[0], 'click');
//         helpers.triggerEvent(EmailBrandingOptionsCheckboxes[2], 'click');
//
//       });
//
//
//       test("the buttons for moving to a new or existing folder are showing", () => {
//
//         expect(formControls.querySelector('button[value=move-to-new-folder]')).not.toBeNull();
//         expect(formControls.querySelector('button[value=move-to-existing-folder]')).not.toBeNull();
//         expect(formControls.querySelector('button[value=move-to-new-folder]').getAttribute('aria-expanded')).toEqual('false');
//         expect(formControls.querySelector('button[value=move-to-existing-folder]').getAttribute('aria-expanded')).toEqual('false');
//
//       });
//
//       test("should make the current controls sticky", () => {
//
//         // the class the sticky JS hooks into should be present
//         expect(formControls.querySelector('#items_selected .js-stick-at-bottom-when-scrolling')).not.toBeNull();
//
//         // .recalculate should have been called so the sticky JS picks up the controls
//         expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);
//
//         // mode should have been set to 'default' as the controls only have one part
//         expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
//         expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('default');
//
//       });
//    });
  });
//
})
