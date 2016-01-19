(function(Modules) {
  "use strict";

  if (!document.queryCommandSupported('copy')) return;

  Modules.ApiKey = function() {

    const states = {
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

      const $component = $(component),
            key = $component.data('key');

      $component
        .html(states.keyVisible(key))
        .attr('aria-live', 'polite')
        .on(
          'click', '.api-key-button-copy', () =>
            this.copyKey(
              $('.api-key-key', component)[0], () =>
                $component.html(states.keyCopied)
            )
        )
        .on(
          'click', '.api-key-button-show', () =>
            $component.html(states.keyVisible(key))
        );

    };
  };

})(window.GOVUK.Modules);
