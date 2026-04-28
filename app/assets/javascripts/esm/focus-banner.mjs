import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 2015 Classes -
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
    if (!isSupported()) {
      return this;
    }

    // focus any error banners when the page loads
    const $bannerEl = document.querySelector('.banner-dangerous');
    if ($bannerEl) {
      this.focusBanner($bannerEl);
    }

    // focus success and error banners when they appear in any content updates
    document.addEventListener('updateContent.onafterupdate', (event) => {
      const el = event.detail.el[0];
      const $bannerEl = el.classList.contains("banner-dangerous") ? el : el.querySelector(".banner-dangerous");
      if ($bannerEl) {
        this.focusBanner($bannerEl);
      }
    });
  }

  focusBanner($bannerEl) {
    $bannerEl.setAttribute('tabindex', '-1');
    $bannerEl.focus();
    $bannerEl.addEventListener('blur', () => {
      $bannerEl.removeAttribute('tabindex');
    }, { once: true });
  }
}

export default FocusBanner;
