// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

// Focus banners that do not use the GOVUK Design System Error Summary component but still need to
// match its behaviour when they appear
class FocusBanner {
  constructor() {
    if (!document.body.classList.contains('govuk-frontend-supported')) {
      return this;
    }

    // focus any error banners when the page loads
    this.focusBanner($('.banner-dangerous'));

    // focus success and error banners when they appear in any content updates
    $(document).on("updateContent.onafterupdate", function(evt, el) {
      this.focusBanner($(".banner-dangerous, .banner-default-with-tick", el));
    }.bind(this));
  }

  focusBanner ($bannerEl) {
    if ($bannerEl.length === 0) { return; }

    $bannerEl.attr('tabindex', '-1');
    $bannerEl.trigger('focus');
    $bannerEl.on('blur', () => {
      $bannerEl.removeAttr('tabindex');
    });
  }
}

export default FocusBanner;
