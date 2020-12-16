const helpers = require('./support/helpers.js');

const emailPageURL = '/services/6658542f-0cad-491f-bec8-ab8457700ead/service-settings/set-email-branding';
const emailPreviewConfirmationURL = '/services/6658542f-0cad-491f-bec8-ab8457700ead/service-settings/preview-email-branding';
const letterPageURL = '/services/6658542f-0cad-491f-bec8-ab8457700ead/service-settings/set-letter-branding';
const letterPreviewConfirmationURL = '/services/6658542f-0cad-491f-bec8-ab8457700ead/service-settings/preview-letter-branding';

let locationMock;

beforeAll(() => {

  // mock calls to window.location
  // default to the email page, the pathname can be changed inside specific tests
  locationMock = new helpers.LocationMock(emailPageURL);

});

afterAll(() => {

  // reset window.location to its original state
  locationMock.reset();
  require('./support/teardown.js');

});

describe('Preview pane', () => {

  let form;
  let radios;

  beforeEach(() => {

    const brands = {
      "name": "branding_style",
      "label": "Branding style",
      "cssClasses": [],
      "fields": [
        {
          "label": "Department for Education",
          "value": "dfe",
          "checked": true
        },
        {
          "label": "Home Office",
          "value": "ho",
          "checked": false
        },
        {
          "label": "Her Majesty's Revenue and Customs",
          "value": "hmrc",
          "checked": false
        },
        {
          "label": "Department for Work and Pensions",
          "value": "dwp",
          "checked": false
        }
      ]
    };

    // set up DOM
    document.body.innerHTML =
      `<form method="post" action="${emailPageURL}" autocomplete="off" data-preview-type="email" novalidate>
        <div class="govuk-grid-row"></div>
        <div class="govuk-grid-row">
          <div class="govuk-grid-column-full">
            <div data-module="autofocus">
              <div class="live-search js-header" data-module="live-search" data-targets=".govuk-radios__item">
                <div class="form-group">
                  <label class="form-label" for="search">
                      Search branding styles by name
                  </label>
                  <input autocomplete="off" class="form-control form-control-1-1 " id="search" name="search" required="" rows="8" type="search" value="">
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="page-footer">
          <button type="submit" class="govuk-button">Preview</button>
        </div>
      </form>`;

    document.querySelector('.govuk-grid-column-full').appendChild(helpers.getRadioGroup(brands));
    form = document.querySelector('form');
    radios = form.querySelector('fieldset');

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // we run the previewPane.js script every test
    // the module cache needs resetting each time for the script to execute
    jest.resetModules();

  });

  describe("If the page type is 'email'", () => {

    describe("When the page loads", () => {

      test("it should add the preview pane", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(document.querySelector('iframe')).not.toBeNull();

      });

      test("it should change the form to submit the selection instead of posting to a preview page", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(form.getAttribute('action')).toEqual(emailPreviewConfirmationURL);

      });

      test("the preview pane should show the page for the selected brand", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        const selectedValue = Array.from(radios.querySelectorAll('input[type=radio]')).filter(radio => radio.checked)[0].value;

        expect(document.querySelector('iframe').getAttribute('src')).toEqual(`/_email?branding_style=${selectedValue}`);

      });

      test("the submit button should change from 'Preview' to 'Save'", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(document.querySelector('button[type=submit]').textContent).toEqual('Save');

      });

    });

    describe("If the selection changes", () => {

      test("the page shown should match the selected brand", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        const newSelection = radios.querySelectorAll('input[type=radio]')[1];

        helpers.moveSelectionToRadio(newSelection);

        expect(document.querySelector('iframe').getAttribute('src')).toEqual(`/_email?branding_style=${newSelection.value}`);

      });

    });

  });

  describe("If the page type is 'letter'", () => {

    beforeEach(() => {

      // set page URL and page type to 'letter'
      window.location.pathname = letterPreviewConfirmationURL;
      form.setAttribute('data-preview-type', 'letter');

    });

    describe("When the page loads", () => {

      test("it should add the preview pane", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(document.querySelector('iframe')).not.toBeNull();

      });

      test("it should change the form to submit the selection instead of posting to a preview page", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(form.getAttribute('action')).toEqual(letterPreviewConfirmationURL);

      });

      test("the preview pane should show the page for the selected brand", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        const selectedValue = Array.from(radios.querySelectorAll('input[type=radio]')).filter(radio => radio.checked)[0].value;

        expect(document.querySelector('iframe').getAttribute('src')).toEqual(`/_letter?branding_style=${selectedValue}`);

      });

      test("the submit button should change from 'Preview' to 'Save'", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        expect(document.querySelector('button[type=submit]').textContent).toEqual('Save');

      });

    });

    describe("If the selection changes", () => {

      test("the page shown should match the selected brand", () => {

        // run preview pane script
        require('../../app/assets/javascripts/previewPane.js');

        const newSelection = radios.querySelectorAll('input[type=radio]')[1];

        helpers.moveSelectionToRadio(newSelection);

        expect(document.querySelector('iframe').getAttribute('src')).toEqual(`/_letter?branding_style=${newSelection.value}`);

      });

    });

  });

});
