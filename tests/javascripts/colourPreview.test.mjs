import ColourPreview from '../../app/assets/javascripts/esm/colour-preview.mjs'
import * as helpers from './support/helpers.js'

describe('Colour preview', () => {

  let textbox;
  let swatchEl; 

  beforeEach(() => {

    // add class to mimic IRL 
    document.body.classList.add('govuk-frontend-supported')

    // set up DOM
    document.body.innerHTML = `
      <div class="govuk-form-group">
        <label class="govuk-label" for="colour">
          Colour
        </label>
        <div class="govuk-input__wrapper">
          <div class="govuk-input__prefix" aria-hidden="true">#</div>
          <input class="govuk-input govuk-input--width-6" id="colour-2" name="colour" rows="8" type="text" value="" data-notify-module="colour-preview">
        </div>
      </div>`;

    textbox = document.querySelector('input[type=text]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe("When the page loads", () => {

    test("It should add a swatch element for the preview", () => {

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      expect(swatchEl).not.toBeNull();

    });

    test("If the textbox is empty it should make the swatch white", () => {

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // textbox defaults to empty
      // colours are output in RGB
        expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');
    });

    test("If the textbox has a value which is a 6-character hex code it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '#00FF00');

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // textbox defaults to empty
      // colours are output in RGB
        expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');
    });

    test("If the textbox has a value which is a 3-character hex code it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '#0F0');

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("The textbox has a value which is a 6-character hex code without a leading # it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '00FF00');

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("The textbox has a value which is a 3-character hex code without a leading # it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '0F0');

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("If the textbox has a value which isn't a hex code it should make the swatch white", () => {

      textbox.setAttribute('value', 'green');

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

      // colours are output in RGB
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

  });

  describe("When input is added to the textbox", () => {

    beforeEach(() => {

      // start the module
      new ColourPreview(document.querySelector('[data-notify-module="colour-preview"]'))
      swatchEl = document.querySelector('.govuk-input__colour-preview');

    });

    test("If the textbox is empty it should make the swatch white", () => {

      helpers.triggerEvent(textbox, 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

    test("If the textbox has a value which is a hex code it should add that colour to the swatch", () => {

      textbox.setAttribute('value', '#00FF00');

      helpers.triggerEvent(textbox, 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

    test("If the textbox has a value which isn't a hex code it should make the swatch white", () => {

      textbox.setAttribute('value', 'green');

      helpers.triggerEvent(textbox, 'input');

      // textbox defaults to empty
      expect(swatchEl.style.background).toEqual('rgb(255, 255, 255)');

    });

    test("If there is leading and trailing space the preview still works", () => {

      textbox.setAttribute('value', '  #00FF00 ');

      helpers.triggerEvent(textbox, 'input');

      expect(swatchEl.style.background).toEqual('rgb(0, 255, 0)');

    });

  });

});
