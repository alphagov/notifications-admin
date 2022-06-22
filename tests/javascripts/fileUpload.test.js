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

  test("An 'upload' button should be added", () => {

    // start module
    window.GOVUK.modules.start();

    expect(form.querySelector('button[type=button]')).not.toBeNull();

    // Note: the existing form controls are also hidden but this is through CSS so out of scope

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
      window.GOVUK.modules.start();

      uploadControl.addEventListener('click', fileUploadClickCallback);

      helpers.triggerEvent(form.querySelector('button[type=button]'), 'click');
      helpers.triggerEvent(uploadControl, 'change', { eventInit: { bubbles: true } });

    });

    test("It should click the file upload control", () => {

      expect(fileUploadClickCallback).toHaveBeenCalled();

    });

    test("The form should submit", () => {

      expect(form.submit).toHaveBeenCalled();

    });

    test("It should replace the upload button with a notice that uploading has started and a cancel upload button", () => {

      var uploadingContent = form.querySelector('p.file-upload-loading-content');

      expect(uploadingContent).not.toBeNull();

      var cancelLink = uploadingContent.querySelector("a[href='']");

      expect(cancelLink).not.toBeNull();

      // the new content replaces the 'upload' button so needs focusing so:
      // - focus is not lost
      // - the text in the paragraph is announced to screen readers
      expect(document.activeElement).toBe(uploadingContent);

    });

  });

});
