(function(Modules) {
  "use strict";

  if (
    !('oninput' in document.createElement('input'))
  ) return;

  const tagPattern = /\(\([^\)\(]+\)\)/g;

  Modules.HighlightTags = function() {

    this.start = function(textarea) {

      this.$textbox = $(textarea)
        .wrap(`
          <div class='textbox-highlight-wrapper' />
        `)
        .after(this.$background = $(`
          <div class="textbox-highlight-background" aria-hidden="true" />
        `))
        .on("input", this.update);

      this.initialHeight = this.$textbox.height();

      this.$background.css({
        'width': this.$textbox.outerWidth(),
        'border-width': this.$textbox.css('border-width')
      });

      this.$textbox
        .trigger("input");

    };

    this.resize = () => this.$textbox.height(
      Math.max(
        this.initialHeight,
        this.$background.outerHeight()
      )
    );

    this.escapedMessage = () => $('<div/>').text(this.$textbox.val()).html();

    this.replacePlaceholders = () => this.$background.html(
      this.escapedMessage().replace(
        tagPattern, match => `<span class='placeholder'>${match}</span>`
      )
    );

    this.update = () => this.replacePlaceholders() && this.resize();

  };

})(window.GOVUK.Modules);
