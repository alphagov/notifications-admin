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

class RemoveInPresenceOf {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$elementToRemove = $module;
    const observer = new MutationObserver(function () {
      if (document.getElementById(this.$elementToRemove.dataset.targetElementId)) {
        this.$elementToRemove.parentNode.removeChild(this.$elementToRemove);
        observer.disconnect();
      }
    }.bind(this));

    observer.observe(document.getElementById('main-content'), { childList: true, subtree: true });

  }
}

export default RemoveInPresenceOf;
