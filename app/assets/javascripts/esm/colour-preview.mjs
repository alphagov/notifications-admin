import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class ColourPreview {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.isHexColourValue = value => value.match(/^#?(?:[0-9A-F]{3}){1,2}$/i);
    this.addHashIfNeeded = value => value.charAt(0) === '#' ? value : '#' + value;
    this.colourOrWhite = value => this.isHexColourValue(value) ? this.addHashIfNeeded(value) : '#FFFFFF';

    this.$input = $module;

    // We expect the colour preview module to only ever be applied to a GOV.UK Design System text input with a prefix,
    // which wraps the text input inside a `govuk-input__wrapper` div.
    const $appendToElement = this.$input.parentNode;

    this.$colourPreviewElement = document.createElement('span');
    this.$colourPreviewElement.setAttribute('class', 'govuk-input__colour-preview');
    $appendToElement.append(this.$colourPreviewElement);

    this.applyBackgroundColour();

    this.$input.addEventListener("input", () => {
      this.applyBackgroundColour();
    });
  }

  applyBackgroundColour() {
    this.$colourPreviewElement.style.background = this.colourOrWhite(this.$input.value.trim());
  }
}

export default ColourPreview;