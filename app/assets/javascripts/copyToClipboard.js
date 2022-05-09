(function(Modules) {
  "use strict";

  if (!document.queryCommandSupported('copy')) return;

  Modules.CopyToClipboard = function() {

    const states = {
      'valueVisible': (options) => `
        <span class="copy-to-clipboard__value">${options.valueLabel ? '<span class="govuk-visually-hidden">' + options.thing + ': </span>' : ''}${options.value}</span>
        <span class="copy-to-clipboard__notice govuk-visually-hidden" aria-live="assertive">
          ${options.onload ? '' : options.thing + ' returned to page, press button to copy to clipboard'}
        </span>
        <button class="govuk-button govuk-button--secondary copy-to-clipboard__button--copy">
          Copy ${options.thing} to clipboard${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}
        </button>
      `,
      'valueCopied': (options) => `
        <span class="copy-to-clipboard__notice" aria-live="assertive">
          <span class="govuk-visually-hidden">${options.thing} </span>Copied to clipboard<span class="govuk-visually-hidden">, press button to show in page</span>
        </span>
        <button class="govuk-button govuk-button--secondary copy-to-clipboard__button--show">
          Show ${options.thing}${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}
        </button>
      `
    };

    this.getRangeFromElement = function (copyableElement) {
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

    this.copyValueToClipboard = function(copyableElement, callback) {
      var selection = window.getSelection ? window.getSelection() : document.selection,
          range = this.getRangeFromElement(copyableElement);

      selection.removeAllRanges();
      selection.addRange(range);
      document.execCommand('copy');
      selection.removeAllRanges();
      callback();
    };

    this.start = function(component) {

      const $component = $(component),
            stateOptions = {
              value: $component.data('value'),
              thing: $component.data('thing')
            },
            name = $component.data('name');

      // if the name is distinct from the thing:
      // - it will be used in the rendering
      // - the value won't be identified by a heading so needs its own label
      if (name !== stateOptions.thing) {
        stateOptions.name = name;
        stateOptions.valueLabel = true;
      }

      $component
        .addClass('copy-to-clipboard')
        .css('min-height', $component.height())
        .html(states.valueVisible($.extend({ 'onload': true }, stateOptions)))
        .on(
          'click', '.copy-to-clipboard__button--copy', () =>
            this.copyValueToClipboard(
              $('.copy-to-clipboard__value', component)[0], () =>
                $component
                  .html(states.valueCopied(stateOptions))
                  .find('.govuk-button').focus()
            )
        )
        .on(
          'click', '.copy-to-clipboard__button--show', () =>
            $component
              .html(states.valueVisible(stateOptions))
              .find('.govuk-button').focus()
        );

      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

    };
  };

})(window.GOVUK.Modules);
