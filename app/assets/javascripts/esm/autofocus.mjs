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

class Autofocus {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.$component = $module;
    const forceFocus = Boolean(this.$component.dataset.forceFocus);
    const arrayOfTargetElements = ['input', 'textarea', 'select'];
    // if the page loads with a scroll position, we can't assume the item to focus onload
    // is still where users intend to start
    if ((window.scrollY > 0) && !forceFocus) { return; }

    // See if the component itself is something we want to send focus to
    // Otherwise look inside the component to see if there are any elements
    // we want to send focus to
    let target = arrayOfTargetElements.includes(this.$component.tagName.toLowerCase())
      ? this.$component
      : this.$component.querySelector(arrayOfTargetElements.join(','));
    target.focus();
  }
}

export default Autofocus;
