(function(Modules) {
  "use strict";

  if (
    !('oninput' in document.createElement('input'))
  ) return;

  const tagPattern = /\(\(([^\)\((\?)]+)(\?\?)?([^\)\(]*)\)\)/g;

  Modules.EnhancedTextbox = function() {

    this.start = function(textarea) {

      let visibleTextbox;

      this.highlightPlaceholders = (
        typeof textarea.data('highlightPlaceholders') === 'undefined' ||
        !!textarea.data('highlightPlaceholders')
      );

      this.$textbox = $(textarea)
        .wrap(`
          <div class='textbox-highlight-wrapper' />
        `)
        .after(this.$background = $(`
          <div class="textbox-highlight-background" aria-hidden="true" />
        `))
        .on("input", this.update);

      $(window).on("resize", this.resize);

      visibleTextbox = this.$textbox.clone().appendTo("body").css({
        position: 'absolute',
        visibility: 'hidden',
        display: 'block'
      });
      this.initialHeight = visibleTextbox.height();

      this.$background.css({
        'border-width': this.$textbox.css('border-width')
      });

      visibleTextbox.remove();

      this.$textbox
        .trigger("input");

    };

    this.resize = () => {

      this.$background.width(this.$textbox.width());

      this.$textbox.height(
        Math.max(
          this.initialHeight,
          this.$background.outerHeight()
        )
      );

      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

    };

    this.contentEscaped = () => $('<div/>').text(this.$textbox.val()).html();

    this.contentReplaced = () => this.contentEscaped().replace(
      tagPattern, (match, name, separator, value) => value && separator ?
        `<span class='placeholder-conditional'>((${name}??</span>${value}))` :
        `<span class='placeholder'>((${name}${value}))</span>`
    );

    this.update = () => {

      this.$background.html(
        this.highlightPlaceholders ? this.contentReplaced() : this.contentEscaped()
      );

      this.resize();

    };

  };

})(window.GOVUK.Modules);
