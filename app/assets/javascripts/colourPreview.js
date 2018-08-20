(function(Modules) {
  "use strict";

  let isSixDigitHex = value => value.match(/^#[0-9A-F]{6}$/i);
  let colourOrWhite = value => isSixDigitHex(value) ? value : '#FFFFFF';

  Modules.ColourPreview = function() {

    this.start = component => {

      this.$input = $('input', component);
      this.$preview = $('.textbox-colour-preview', component);

      this.$input
        .on('change keyup', this.update)
        .trigger('change');

    };

    this.update = () => this.$preview.css(
      'background', colourOrWhite(this.$input.val())
    );

  };

})(window.GOVUK.Modules);
