(function(Modules) {
  "use strict";

  let isSixDigitHex = value => value.match(/^#[0-9A-F]{6}$/i);
  let colourOrWhite = value => isSixDigitHex(value) ? value : '#FFFFFF';

  Modules.ColourPreview = function() {

    this.start = component => {

      this.$input = $(component);

      this.$input.closest('.govuk-form-group').append(
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

})(window.GOVUK.Modules);
