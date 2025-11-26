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

class UpdateStatus {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$module = $module;
    this.$textbox = document.getElementById(this.$module.dataset.target);
    this.throttleOn = false;
    this.callsHaveBeenThrottled = false;
    this.timeout = null;
  }

  getRenderer($module, response) {
    $module.innerHTML = response.html;
  }

  throttle(func, limit) {
    return (...args) => {
      if (this.throttleOn) {
        this.callsHaveBeenThrottled = true;
      } else {
        func.apply(this, args);
        this.throttleOn = true;
      }

      clearTimeout(this.timeout);

      this.timeout = setTimeout(() => {
        this.throttleOn = false;
        if (this.callsHaveBeenThrottled) func.apply(this, args);
        this.callsHaveBeenThrottled = false;
      }, limit);
    };
  }

  init() {
    const id = 'update-status';
    this.$module.setAttribute('id', id);
    const ariaDescribedby = this.$textbox.getAttribute('aria-describedby') || '';

    this.$textbox.setAttribute(
      'aria-describedby',
      `${ariaDescribedby}${ariaDescribedby ? ' ' : ''}${id}`
    );

    this.$textbox.addEventListener('input', this.throttle(this.update.bind(this), 150).bind(this));
    this.$textbox.dispatchEvent(new Event('input'));
  }

  async update() {
    const url = this.$module.dataset.updatesUrl;
    const formData = new URLSearchParams(new FormData(this.$textbox.closest('form'))).toString();

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        this.getRenderer(this.$module, data);
      }
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  }
}

export default UpdateStatus;
