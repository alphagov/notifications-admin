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
      <form method="post" enctype="multipart/form-data" class="" data-notify-module="file-upload">
        <label class="file-upload-label" for="file">
          Upload a PNG logo
        </label>
        <input class="file-upload-field" data-button-text="Upload logo" id="file" name="file" type="file">
        <button class="govuk-button file-upload-submit">Submit</button>
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
    window.GOVUK.notifyModules.start();

    helpers.triggerEvent(window, 'pageshow');

    expect(form.reset).toHaveBeenCalled();

  });

  test("An 'upload' button should be added", () => {

    // start module
    window.GOVUK.notifyModules.start();

    var uploadButton = form.querySelector('button');

    expect(uploadButton).not.toBeNull();

    // Note: the existing form controls are also hidden but this is through CSS so out of scope

  });

  test("If the page loads with validation errors, they should be added to the 'upload' button", () => {

    var buttonLabel;

    uploadLabel.innerHTML += '<span class="error-message">PNG images only!</span>';

    // start module
    window.GOVUK.notifyModules.start();

    buttonLabel = form.querySelector('label.file-upload-button-label');

    expect(buttonLabel).not.toBeNull();

    // The button's label should include its existing text and the validation errors added together
    expect(buttonLabel.textContent.trim().replace(/\s{2,}/g, ' ')).toEqual("Upload logo PNG images only!");

  });

  /*
    The file is selected by a click event on the input[type=file] control and the user choosing
    a file from the OS dialog this opens. This creates an onchange event we use to submit the form.

    We can't simulate the user choosing a file so we test the behaviours resulting from the click
    and onchange events.
  */
  describe("If the 'upload' button is clicked", () => {

    var fileUploadClickCallback;

    beforeEach(() => {

      fileUploadClickCallback = jest.fn(() => {});
      form.submit = jest.fn(() => {});

      // start module
      window.GOVUK.notifyModules.start();

      uploadControl.addEventListener('click', fileUploadClickCallback);

      // click the 'upload' button
      helpers.triggerEvent(form.querySelector('button'), 'click');

      // fake the 'onchange' event triggered in browsers by selection of a file
      helpers.triggerEvent(uploadControl, 'change', { eventInit: { bubbles: true } });

    });

    test("It should click the file upload control", () => {

      expect(fileUploadClickCallback).toHaveBeenCalled();

    });

    test("The form should submit", () => {

      expect(form.submit).toHaveBeenCalled();

    });

    test("It should replace the upload button with one for cancelling the upload", () => {

      var cancelLink = form.querySelector("a.file-upload-button");

      expect(cancelLink).not.toBeNull();

      // the cancel button should be focused
      expect(document.activeElement).toBe(cancelLink);

    });

  });

});
