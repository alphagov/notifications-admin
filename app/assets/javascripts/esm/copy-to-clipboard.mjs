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

class CopyToClipboard {
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
    this.name = this.$module.dataset.name;

    // if the name is distinct from the thing:
    // - it will be used in the rendering
    // - the value won't be identified by a heading so needs its own label
    if (this.name.toLowerCase() !== this.stateOptions.thing.toLowerCase()) {
      this.stateOptions.name = this.name;
      this.stateOptions.valueLabel = true;
    }
    this.$module.classList.add('copy-to-clipboard');
    
    // button and SR elements are added
    this.updateHTML('valueVisible', {...{ 'onload': true }, ...this.stateOptions}, this.$module);

    this.$module.addEventListener('click', (e) => {
      const $target = e.target;
      if ($target.tagName === "BUTTON") {
        const buttonWasClicked = $target.classList.contains('copy-to-clipboard__button--show');
        if (buttonWasClicked) {
          this.updateHTML(buttonWasClicked, this.stateOptions, this.$module, $target);
        } else {
          this.copyValueToClipboard(
            this.getRangeFromElement(this.$module.querySelector('.copy-to-clipboard__value'))
          );
          this.updateHTML(buttonWasClicked, this.stateOptions, this.$module, $target);
        };
      }
    });

    if ('stickAtBottomWhenScrolling' in window.GOVUK) {
      window.GOVUK.stickAtBottomWhenScrolling.recalculate();
    }
  }
  
  updateHTML (buttonWasClicked, stateOptions, $module, $button) {
    // use the correct state key to update the HTML
    // if the button was clicked then content needs to change to reflect that
    // e.g say 'copied, ....
    const stateKey = buttonWasClicked ? 'valueVisible' : 'valueCopied';
    const state = this.states[stateKey](stateOptions);

    $module.querySelectorAll('.copy-to-clipboard__value').forEach(e => e.remove());
    if (state.value !== '') {
      $module.insertAdjacentHTML('afterbegin', state.value);
    }
    let $clipboardNoticeEl = $module.querySelector('.copy-to-clipboard__notice');
    $clipboardNoticeEl.innerHTML = state.notice.content;
    $clipboardNoticeEl.setAttribute('class', state.notice.classes);

    !$button ? this.generateButton(state) : this.updateButton(state, $button);
  }

  generateButton (state) {
    let $newButton = document.createElement('button');
    $newButton.setAttribute('class', state.button.classes);
    $newButton.innerHTML = state.button.content;
    this.$module.append($newButton);
  }

  updateButton (state, $button) {
    $button.innerHTML = state.button.content;
    $button.removeAttribute('class');
    $button.setAttribute('class', state.button.classes);
  }

  async copyValueToClipboard(text){
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
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
  };
}

export default CopyToClipboard;
