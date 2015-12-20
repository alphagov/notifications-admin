(function(Modules) {
  "use strict";

  Modules.HighlightTags = function() {

    this.start = function(textarea) {

      this.$textbox = $(textarea)
        .wrap(
          "<div class='textbox-highlight-wrapper' />"
        )
        .after(this.$backgroundMaskForeground = $(
          "<div class='textbox-highlight-background' aria-hidden='true' />" +
          "<div class='textbox-highlight-mask' aria-hidden='true' />" +
          "<div class='textbox-highlight-foreground' aria-hidden='true' />"
        ))
        .on("input", this.update.bind(this))
        .on("scroll", this.maintainScrollParity.bind(this));

      this.$textbox
        .trigger("input");

    };

    this.update = function(event) {
      this.$backgroundMaskForeground.html(
        replaceTags(this.$textbox.val())
      );
    };

    this.maintainScrollParity = function() {
      this.$backgroundMaskForeground.scrollTop(
        this.$textbox.scrollTop()
      );
    };

  };

  function replaceTag(match) {
    return ("<span class='tag'>" + match + "</span>");
  }

  function replaceTags(content) {
    return content.replace(/\(\([^\)\(]+\)\)/g, replaceTag);
  }

})(window.GOVUK.Modules);
