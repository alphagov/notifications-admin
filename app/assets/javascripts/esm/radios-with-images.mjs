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

class RadiosWithImages {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$module = $module;
    this.$module.addEventListener('click', this.handleImageClick);
    this.$module.style.cursor = 'pointer';
  }

  handleImageClick () {
    const image_input = this.nextElementSibling.querySelector(`[aria-describedby="${this.id}"]`);
    image_input.checked = true;
    image_input.focus();
  };
}

export default RadiosWithImages;