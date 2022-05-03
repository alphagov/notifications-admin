const helpers = require('./support/helpers.js');

beforeAll(() => {

  // Stub out JS from window.GOVUK namespace used by this component
  window.GOVUK.Frontend = {
    Button: function () {
      return {
        init: function () {}
      }
    }
  };

  require('../../app/assets/javascripts/fileUpload.js');

});

afterAll(() => {
  require('./support/teardown.js');
});

describe('File upload', () => {

  let form;
  let fileUpload;

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <form method="post" enctype="multipart/form-data" class="" data-module="file-upload">
        <label class="file-upload-label" for="file">
          Upload a PNG logo
        </label>
        <input class="file-upload-field" data-button-text="Upload logo" id="file" name="file" type="file">
        <button type="submit" class="govuk-button file-upload-submit">Submit</button>
      </form>`;

    form = document.querySelector('form');
    uploadLabel = form.querySelector('label.file-upload-label');
    uploadControl = form.querySelector('input.file-upload-field');
    uploadSubmit = form.querySelector('button.file-upload-submit')

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  test("If the page loads, from a new or existing navigation, the form should reset", () => {

    form.reset = jest.fn(() => {});

    // start module
    window.GOVUK.modules.start();

    helpers.triggerEvent(window, 'pageshow');

    expect(form.reset).toHaveBeenCalled();

  });

  test("An 'upload' button should be added and the existing form contents hidden", () => {

    // start module
    window.GOVUK.modules.start();

    expect(form.querySelector('button[type=button]')).not.toBeNull();
    expect(uploadLabel.hasAttribute('hidden')).toBe(true);
    expect(uploadControl.hasAttribute('hidden')).toBe(true);
    expect(uploadSubmit.hasAttribute('hidden')).toBe(true);

  });

  /*
    The file is selected by a click event on the input[type=file] control and the user choosing
    a file from the OS dialog this opens. This creates an onchange event we use to submit the form.

    We can't simulate the user choosing a file so we test the behaviours resulting from the click
    and onchange events.
  */
  test("If the 'upload' button is clicked, it should click the file upload control", () => {

    // start module
    window.GOVUK.modules.start();

    var fileUploadClickCallback = jest.fn(() => {});
    uploadControl.addEventListener('click', fileUploadClickCallback);

    helpers.triggerEvent(form.querySelector('button[type=button]'), 'click');

    expect(fileUploadClickCallback).toHaveBeenCalled();

  });

  describe("If the state of the upload form control changes (from clicking the 'upload' button)", () => {

    beforeEach(() => {

      form.submit = jest.fn(() => {});

      // start module
      window.GOVUK.modules.start();

      helpers.triggerEvent(uploadControl, 'change', { eventInit: { bubbles: true } });

    });

    test("The form should submit", () => {

      expect(form.submit).toHaveBeenCalled();

    });

    test("It should add a link to cancel the upload by reloading the page", () => {

      expect(form.querySelector("a[href='']")).not.toBeNull();

    });

  });

});
