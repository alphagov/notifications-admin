const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/colourPreview.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Colour preview', () => {

  let field;
  let textbox;
  let swatchEl;

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <div class="govuk-form-group">
        <label class="govuk-form-label" for="colour">
          Colour
        </label>
        <input class="govuk-input govuk-input--width-6" id="colour" name="colour" rows="8" type="text" value="" data-module="colour-preview">
      </div>`;

    field = document.querySelector('.govuk-form-group');
    textbox = document.querySelector('input[type=text]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe("When the page loads", () => {

    test("It should add a swatch element for the preview", () => {

      // start the module
      window.GOVUK.modules.start();

      swatchEl = document.querySelector('.textbox-colour-preview');

      expect(swatchEl).not.toBeNull();

    });

    test("If the textbox is empty it should make the swatch white", () => {

      // start the module
      window.GOVUK.modules.start();

      swatchEl = document.querySelector('.textbox-colour-preview');

      // textbox defaults to empty
      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

    test("If the textbox has a value which is a hex code it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '#00FF00');

      // start the module
      window.GOVUK.modules.start();

      swatchEl = document.querySelector('.textbox-colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("If the textbox has a value which isn't a hex code it should make the swatch white", () => {

      textbox.setAttribute('value', 'green');

      // start the module
      window.GOVUK.modules.start();

      swatchEl = document.querySelector('.textbox-colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

  });

  describe("When input is added to the textbox", () => {

    beforeEach(() => {

      // start the module
      window.GOVUK.modules.start();

      swatchEl = document.querySelector('.textbox-colour-preview');

    });

    test("If the textbox is empty it should make the swatch white", () => {

      helpers.triggerEvent(document.querySelector('input[type=text]'), 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

    test("If the textbox has a value which is a hex code it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '#00FF00');

      helpers.triggerEvent(document.querySelector('input[type=text]'), 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("If the textbox has a value which isn't a hex code it should make the swatch white", () => {

      textbox.setAttribute('value', 'green');

      helpers.triggerEvent(document.querySelector('input[type=text]'), 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

  });

});
