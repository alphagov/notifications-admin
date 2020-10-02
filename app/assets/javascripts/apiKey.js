(function(Modules) {
  "use strict";

  if (!document.queryCommandSupported('copy')) return;

  Modules.ApiKey = function() {

    const states = {
      'keyVisible': (options) => `
        <span class="api-key__key">
          ${options.keyLabel ? '<span class="govuk-visually-hidden">' + options.thing + ': </span>' : ''}${options.key}
        </span>
        <span class="api-key__notice govuk-visually-hidden" aria-live="assertive">
          ${options.onload ? '' : options.thing + ' returned to page, press button to copy to clipboard'}
        </span>
        <button class="govuk-button govuk-button--secondary api-key__button--copy">
          Copy ${options.thing} to clipboard${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}
        </button>
      `,
      'keyCopied': (options) => `
        <span class="api-key__notice" aria-live="assertive">
          <span class="govuk-visually-hidden">${options.thing} </span>Copied to clipboard<span class="govuk-visually-hidden">, press button to show in page</span>
        </span>
        <button class="govuk-button govuk-button--secondary api-key__button--show">
          Show ${options.thing}${options.name ? '<span class="govuk-visually-hidden"> for ' + options.name + '</span>' : ''}
        </button>
      `
    };

    this.getRangeFromElement = function (keyElement) {
      const range = document.createRange();
      const childNodes = Array.prototype.slice.call(keyElement.childNodes);
      let prefixIndex = -1;

      childNodes.forEach((el, idx) => {
        if ((el.nodeType === 1) && el.classList.contains('govuk-visually-hidden')) {
          prefixIndex = idx;
        }
      });

      range.selectNodeContents(keyElement);
      if (prefixIndex !== -1) { range.setStart(keyElement, prefixIndex + 1); }

      return range;
    };

    this.copyKey = function(keyElement, callback) {
      var selection = window.getSelection ? window.getSelection() : document.selection,
          range = this.getRangeFromElement(keyElement);

      selection.removeAllRanges();
      selection.addRange(range);
      document.execCommand('copy');
      selection.removeAllRanges();
      callback();
    };

    this.start = function(component) {

      const $component = $(component),
            stateOptions = {
              key: $component.data('key'),
              thing: $component.data('thing')
            },
            name = $component.data('name');

      // if the name is distinct from the thing:
      // - it will be used in the rendering
      // - the key won't be identified by a heading so needs its own label
      if (name !== stateOptions.thing) {
        stateOptions.name = name;
        stateOptions.keyLabel = true;
      }

      $component
        .addClass('api-key')
        .css('min-height', $component.height())
        .html(states.keyVisible($.extend({ 'onload': true }, stateOptions)))
        .on(
          'click', '.api-key__button--copy', () =>
            this.copyKey(
              $('.api-key__key', component)[0], () =>
                $component
                  .html(states.keyCopied(stateOptions))
                  .find('.govuk-button').focus()
            )
        )
        .on(
          'click', '.api-key__button--show', () =>
            $component
              .html(states.keyVisible(stateOptions))
              .find('.govuk-button').focus()
        );

      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

    };
  };

})(window.GOVUK.Modules);
