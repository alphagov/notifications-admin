import { isSupported } from 'govuk-frontend';
import { stickAtBottomWhenScrolling } from './stick-to-window-when-scrolling.mjs';

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

    // guard against CSS not being loaded
    if (window.getComputedStyle($module)['position'] !== 'relative') {
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
          this.$backgroundHighlightElement.offsetHeight
      )}px`;

    stickAtBottomWhenScrolling.recalculate();
  }

  contentReplaced () {
    const fragment = document.createDocumentFragment();
    const text = this.$textbox.value;
    let lastIndex = 0;

    for (const match of text.matchAll(this.tagPattern)) {
      // append plain text before the placeholder starts
      fragment.append(text.slice(lastIndex, match.index));

      const [
        fullMatch,  // index 0: full match
        name,       // index 1: capture group 1
        separator,  // index 2: capture group 2
        value       // index 3: capture group 3
      ] = match;
      const $span = document.createElement('span');

      if (value && separator) {
        $span.className = 'placeholder-conditional';
        $span.textContent = `((${name}??`;
        fragment.append($span, `${value}))`);
      } else {
        $span.className = 'placeholder';
        $span.textContent = `((${name}${value}))`;
        fragment.append($span);
      }

      // update with the index where the current placeholder ends
      lastIndex = match.index + fullMatch.length;
    }

    // append any remaining trailing text
    fragment.append(text.slice(lastIndex));
    return fragment;
  }

  update () {
    // clear everything that's in the container to avoid any potential XSS
    this.$backgroundHighlightElement.textContent = '';

    if (this.highlightPlaceholders) {
      this.$backgroundHighlightElement.append(this.contentReplaced());
    } else {
      this.$backgroundHighlightElement.textContent = this.$textbox.value;
    }

    this.resize();
  }
}

export default EnhancedTextbox;
