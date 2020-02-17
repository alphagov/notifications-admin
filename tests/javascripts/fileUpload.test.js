const helpers = require('./support/helpers.js');

beforeAll(() => {
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
          <span class="visually-hidden">Upload a PNG logo</span>
        </label>
        <input class="file-upload-field" id="file" name="file" type="file">
        <label class="file-upload-button" for="file">
          Upload logo
        </label>
        <label class="file-upload-filename" for="file"></label>
        <button type="submit" class="govuk-button file-upload-submit">Submit</button>
      </form>`;

    form = document.querySelector('form');
    uploadControl = form.querySelector('input[type=file]');

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

  describe("If the state of the upload form control changes", () => {

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
