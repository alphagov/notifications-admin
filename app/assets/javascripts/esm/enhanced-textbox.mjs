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

class EnhancedTextbox {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$module = $module;
    this.tagPattern = /\(\(([^\)\((\?)]+)(\?\?)?([^\)\(]*)\)\)/g;
    this.highlightPlaceholders = this.$module.dataset.highlightPlaceholders === 'true';
    this.autofocus = this.$module.dataset.autofocusTextbox === 'true';
    this.$textbox = this.$module;

    // wrap module in a container
    this.$wrappingElement = document.createElement('div');
    this.$wrappingElement.classList.add('govuk-textarea-highlight__wrapper');
    this.$textbox.replaceWith(this.$wrappingElement);
    this.$wrappingElement.appendChild(this.$textbox);

    // append a background container to the module
    this.$backgroundHighlightElement = document.createElement('div');
    this.$backgroundHighlightElement.classList.add('govuk-textarea-highlight__background');
    this.$backgroundHighlightElement.setAttribute('aria-hidden', 'true');
    this.$textbox.after(this.$backgroundHighlightElement);

    this.$textbox.addEventListener("input", this.update.bind(this));
    window.addEventListener("resize", this.resize.bind(this));

    this.$visibleTextbox = this.$textbox.cloneNode(true);
    this.$visibleTextbox.style.position = 'absolute';
    this.$visibleTextbox.style.visibility = 'hidden';
    this.$visibleTextbox.style.display = 'block';
    document.querySelector('body').append(this.$visibleTextbox);
    
    this.initialHeight = this.$visibleTextbox.offsetHeight;

    this.$backgroundHighlightElement.style.borderWidth = 
      window.getComputedStyle(this.$textbox).getPropertyValue('border-width');

    this.$visibleTextbox.remove();
    this.$textbox.dispatchEvent(new Event('input', { bubbles: true }));

    if (this.autofocus) {
      this.$textbox.focus();
    }
  }

  resize () {
    this.$backgroundHighlightElement.style.width = window.getComputedStyle(this.$textbox).width;
    this.$textbox.style.height =
      `${Math.max(
          this.initialHeight,
          // jquery .height and vanilla javascript offsetHeight or clientHeight 
          // take padding values into account in different ways
          // 15px adjustment would suffice to account for 15px padding
          // set in CSS, but adjusting the height by 16px prevents the scrollbar
          // from appearing entirely
          this.$backgroundHighlightElement.offsetHeight + 16
      )}px`;

    if ('stickAtBottomWhenScrolling' in GOVUK) {
      window.GOVUK.stickAtBottomWhenScrolling.recalculate();
    }
  }

  contentEscaped () {
    const $el = document.createElement('div');
    $el.innerHTML = this.$textbox.value;
    return $el.innerHTML;
  }

  contentReplaced () {
    return this.contentEscaped().replace(
      this.tagPattern, (match, name, separator, value) => {
        if (value && separator) {
          return `<span class='placeholder-conditional'>((${name}??</span>${value}))`;
        } else {
          return `<span class='placeholder'>((${name}${value}))</span>`;
        }
      }
    );
  }

  update () {
    this.$backgroundHighlightElement.innerHTML =
      this.highlightPlaceholders ? this.contentReplaced() : this.contentEscaped();

    this.resize();
  }
}

export default EnhancedTextbox;
