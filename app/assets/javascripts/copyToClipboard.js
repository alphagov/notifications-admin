(function(Modules) {
  "use strict";

  if (!document.queryCommandSupported('copy')) return;

  Modules.CopyToClipboard = function() {

    const states = {
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


    this.updateHTML = (stateKey, stateOptions, $component) => {
      const state = states[stateKey](stateOptions);
      let $button = $component.find('.govuk-button');

      $component.find('.copy-to-clipboard__value').remove();
      if (state.value !== '') {
        $component.prepend(state.value);
      }

      $component.find('.copy-to-clipboard__notice').eq(0)
        .html(state.notice.content)
        [0].className = state.notice.classes;

      if ($button.length === 0) {
        $button = $('<button class="govuk-button govuk-button--secondary copy-to-clipboard__button--copy">');
        $component.append($button);
      }

      $button.eq(0)
        .html(state.button.content)
        [0].className = state.button.classes;
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
        .on(
          'click', '.copy-to-clipboard__button--copy', () =>
            this.copyValueToClipboard(
              $('.copy-to-clipboard__value', component)[0], () => {
                this.updateHTML('valueCopied', stateOptions, $component);
              }
            )
        )
        .on(
          'click', '.copy-to-clipboard__button--show', () => {
            this.updateHTML('valueVisible', stateOptions, $component);
          }
        );

      this.updateHTML('valueVisible', ($.extend({ 'onload': true }, stateOptions)), $component);

      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

    };
  };

})(window.GOVUK.NotifyModules);
