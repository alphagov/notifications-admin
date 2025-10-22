import FileUpload from '../../app/assets/javascripts/esm/file-upload.mjs';
import * as helpers from './support/helpers.js';
import { jest } from '@jest/globals';

beforeAll(() => {
  document.body.classList.add('govuk-frontend-supported');
});

describe('File upload', () => {

  let form;
  let uploadLabel;
  let uploadControl;
  let uploadSubmit;

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
    new FileUpload(document.querySelector('[data-notify-module="file-upload"]'));

    helpers.triggerEvent(window, 'pageshow');

    expect(form.reset).toHaveBeenCalled();

  });

  describe("An 'upload' button should visually replace the file field", () => {

    let uploadButton;
    let originalControlId;

    beforeEach(() => {

      originalControlId = uploadControl.id;

      // start module
      new FileUpload(document.querySelector('[data-notify-module="file-upload"]'));

      uploadButton = form.querySelector('button');

    });

    test("Its text should be set by the module config", () => {

      expect(uploadButton).not.toBeNull();
      expect(uploadButton.textContent.trim()).toEqual(uploadControl.dataset.buttonText);

    });

    // We generate links in the error summary to the original field, by id, so our new elements need to match this
    test("The file field's id should be copied to the it and the original rewritten", () => {

      const rewrittenId = `hidden-${originalControlId}`;

      expect(uploadButton.id).toEqual(originalControlId);

      expect(uploadControl.id).not.toEqual(originalControlId);
      expect(uploadLabel.getAttribute('for')).toEqual(uploadControl.id);

    });

    // Note: the existing form controls are also hidden but this is through CSS so out of scope

  });

  test("If the page loads with validation errors, they should be added to the 'upload' button", () => {

    let buttonLabel;

    uploadLabel.innerHTML += '<span class="govuk-error-message">The logo must be a PNG file</span>';

    // start module
    new FileUpload(document.querySelector('[data-notify-module="file-upload"]'));

    buttonLabel = form.querySelector('label.file-upload-button-label');

    expect(buttonLabel).not.toBeNull();

    // The button's label should include its existing text and the validation errors added together
    expect(buttonLabel.textContent.trim().replace(/\s{2,}/g, ' ')).toEqual("Upload logo The logo must be a PNG file");

  });

  /*
    The file is selected by a click event on the input[type=file] control and the user choosing
    a file from the OS dialog this opens. This creates an onchange event we use to submit the form.

    We can't simulate the user choosing a file so we test the behaviours resulting from the click
    and onchange events.
  */
  describe("If the 'upload' button is clicked", () => {

    let fileUploadClickCallback;

    beforeEach(() => {

      fileUploadClickCallback = jest.fn(() => {});
      form.submit = jest.fn(() => {});

      // start module
      new FileUpload(document.querySelector('[data-notify-module="file-upload"]'));

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

      const cancelLink = form.querySelector("a.file-upload-button");

      expect(cancelLink).not.toBeNull();

      // the cancel button should be focused
      expect(document.activeElement).toBe(cancelLink);

    });

  });

});
