(function(Modules) {
  "use strict";

  let isHexColourValue = value => value.match(/^#?(?:[0-9A-F]{3}){1,2}$/i);
  let addHashIfNeeded = value => value.charAt(0) === '#' ? value : '#' + value;
  let colourOrWhite = value => isHexColourValue(value) ? addHashIfNeeded(value) : '#FFFFFF';

  Modules.ColourPreview = function() {

    this.start = component => {

      this.$input = $(component);

      // We expect the colour preview module to only ever be applied to a GOV.UK Design System text input with a prefix,
      // which wraps the text input inside a `govuk-input__wrapper` div.
      const $appendToElement = this.$input.parent();
      $appendToElement.append(
        this.$preview = $('<span class="textbox-colour-preview"></span>')
      );

      this.$input
        .on('input', this.update)
        .trigger('input');

    };

    this.update = () => this.$preview.css(
      'background', colourOrWhite(this.$input.val())
    );

  };

})(window.GOVUK.NotifyModules);
