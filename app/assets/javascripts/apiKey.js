(function(Modules) {
  "use strict";

  Modules.ApiKey = function() {

    const states = {
      'initial': `
        <input type='button' class='api-key-button-show' value='Show API key' />
      `,
      'keyVisibleBasic': key => `
        <span class="api-key-key">${key}</span>
      `,
      'keyVisible': key => `
        <span class="api-key-key">${key}</span>
        <input type='button' class='api-key-button-copy' value='Copy API key to clipboard' />
      `,
      'keyCopied': `
        <span class="api-key-key">Copied to clipboard</span>
        <input type='button' class='api-key-button-show' value='Show API key' />
      `
    };

    this.copyKey = function(keyElement, callback) {
      var selection = window.getSelection ? window.getSelection() : document.selection,
          range = document.createRange();
      selection.removeAllRanges();
      range.selectNodeContents(keyElement);
      selection.addRange(range);
      document.execCommand('copy');
      selection.removeAllRanges();
      callback();
    };

    this.start = function(component) {

      const $component = $(component).html(states.initial).attr('aria-live', 'polite'),
            key = $component.data('key');

      $component
        .on(
          'click', '.api-key-button-show', () =>
            $component.html(
              document.queryCommandSupported('copy') ?
                states.keyVisible(key) : states.keyVisibleBasic(key)
            )
        )
        .on(
          'click', '.api-key-button-copy', () =>
            this.copyKey(
              $('.api-key-key', component)[0], () =>
                $component.html(states.keyCopied)
            )
        );

    };
  };

})(window.GOVUK.Modules);
