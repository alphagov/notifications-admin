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

class CopyToClipBoard {
  constructor($module) {
    if (!isSupported() || !navigator.clipboard) {
      return this;
    }

    this.states = {
      'valueVisible': (options) => {
        return {
          'value': `<span class="copy-to-clipboard__value">${options.valueLabel ?'<span class="govuk-visually-hidden">' +
                      options.thing +': </span>' : ''}${options.value}</span>`,
          'notice': {
            'classes': "copy-to-clipboard__notice govuk-visually-hidden",
            'content': options.onload ? '' : options.thing + ' showing, use button to copy to clipboard'
          },
          'button': {
            'classes': "govuk-button govuk-button--secondary copy-to-clipboard__button--copy",
            'content': `Copy ${options.thing} to clipboard${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}`
          }
        };
      },
      'valueCopied': (options) => {
        return {
          'value': '',
          'notice': {
            'classes': "copy-to-clipboard__notice",
            'content': `<span class="govuk-visually-hidden">${options.thing} </span>Copied to clipboard<span class="govuk-visually-hidden">, use button to show in page</span>`
          },
          'button': {
            'classes': "govuk-button govuk-button--secondary copy-to-clipboard__button--show",
            'content': `Show ${options.thing}${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}`
          }
        };
      }
    };
    this.$module = $module;
    this.stateOptions = {
      value: this.$module.dataset.value,
      thing: this.$module.dataset.thing
    };
    this.name = this.$module.dataset.name.toString();

      // if the name is distinct from the thing:
      // - it will be used in the rendering
      // - the value won't be identified by a heading so needs its own label
      if (this.name.toLowerCase() !== this.stateOptions.thing.toLowerCase()) {
        this.stateOptions.name = this.name;
        this.stateOptions.valueLabel = true;
      }
      this.$module.classList.add('copy-to-clipboard');
      this.$module.style.minHeight = getComputedStyle(this.$module).height;

      this.$module.addEventListener('click', (e) => {
        const target = e.target;
        if (target.matches('.copy-to-clipboard__button--copy')) {
          this.copyValueToClipboard('blue');
          this.updateHTML('valueCopied', this.stateOptions, this.$module);
          // this.copyValueToClipboard(
          //   $('.copy-to-clipboard__value', this.$module, () => {
          //     this.updateHTML('valueCopied', stateOptions, this.$module);
          //   }
          // ))
          
        }
        if (target.matches('.copy-to-clipboard__button--show')) {
          this.copyValueToClipboard('red');
          this.updateHTML('valueVisible', this.stateOptions, this.$module);
        }
      });

      this.updateHTML('valueVisible', {...{ 'onload': true }, ...this.stateOptions}, this.$module);

      if ('stickAtBottomWhenScrolling' in window.GOVUK) {
        window.GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

  }
  updateHTML (stateKey, stateOptions, $module) {
    const state = this.states[stateKey](stateOptions);
    // getElementsBy* works with dynamically added elements
    // whereas querySelector does not
    let $button = this.$module.getElementsByTagName('BUTTON');

    $module.querySelectorAll('.copy-to-clipboard__value').forEach(e => e.remove());
    if (state.value !== '') {
      $module.insertAdjacentHTML('afterbegin', state.value);
    }

    const $clipboardNoticeEl = this.$module.querySelector('.copy-to-clipboard__notice')
    $clipboardNoticeEl.insertAdjacentHTML('afterbegin', state.notice.content);
    $clipboardNoticeEl.setAttribute('class', state.notice.classes);

    if ($button.length === 0) {
      const $newButton = document.createElement('button');
      $newButton.classList.add('govuk-button', 'govuk-button--secondary', 'copy-to-clipboard__button--copy');
      this.$module.append($newButton);
    }

    $button[0].textContent = state.button.content;
    $button[0].setAttribute('class', state.button.classes);
  }

  getRangeFromElement (copyableElement) {
    const range = document.createRange();
    const childNodes = Array.prototype.slice.call(copyableElement.childNodes);
    let prefixIndex = -1;

    childNodes.forEach((el, idx) => {
      if ((el.nodeType === 1) && el.classList.contains('govuk-visually-hidden')) {
        prefixIndex = idx;
      }
    });

    range.selectNodeContents(copyableElement);
    if (prefixIndex !== -1) { range.setStart(copyableElement, prefixIndex + 1); }

    return range;
  }

  async copyValueToClipboard(text){
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
  }
}

export default CopyToClipBoard;