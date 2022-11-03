(function(Modules) {
  "use strict";

  let isHexColourValue = value => value.match(/^#?(?:[0-9A-F]{3}){1,2}$/i);
  let addHashIfNeeded = value => value.charAt(0) === '#' ? value : '#' + value;
  let colourOrWhite = value => isHexColourValue(value) ? addHashIfNeeded(value) : '#FFFFFF';

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

})(window.GOVUK.NotifyModules);
