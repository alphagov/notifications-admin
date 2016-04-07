(function(Modules) {
  "use strict";

  if (
    !('oninput' in document.createElement('input'))
  ) return;

  const tagPattern = /\(\([^\)\(]+\)\)/g;

  const getPlaceholderHint = function(placeholders) {
    if (0 === placeholders.length) {
      return `
        <p>Add fields using ((double brackets))</p>
        <span class='placeholder-hint-action' tabindex='0' role='button'>Show me how</span>
      `;
    }
    if (1 === placeholders.length) {
        return `
          <p>Add fields using ((double brackets))</p>
          <p>You’ll populate the ‘${placeholders[0]}’ field when you send messages using this template</p>
        `;
    }    
    return `
      <p>Add fields using ((double brackets))</p>
      <p>You’ll populate your fields when you send some messages</p>
    `;
  };

  Modules.HighlightTags = function() {

    this.start = function(textarea) {

      this.$textbox = $(textarea)
        .wrap(`
          <div class='textbox-highlight-wrapper' />
        `)
        .after(this.$backgroundMaskForeground = $(`
          <div class="textbox-highlight-background" aria-hidden="true" />
          <div class="textbox-highlight-mask" aria-hidden="true" />
          <div class="textbox-highlight-foreground" aria-hidden="true" />
        `))
        .on("input", this.update);

      this.$placeHolderHint = $('#placeholder-hint')
        .on("click", ".placeholder-hint-action", this.demo);

      this.initialHeight = this.$textbox.height();

      this.$backgroundMaskForeground.css({
        'width': this.$textbox.width(),
        'border-width': this.$textbox.css('border-width')
      });

      this.$textbox
        .trigger("input");

    };

    this.resize = () => this.$textbox.height(
      Math.max(
        this.initialHeight,
        this.$backgroundMaskForeground.outerHeight()
      )
    );

    this.escapedMessage = () => $('<div/>').text(this.$textbox.val()).html();

    this.listPlaceholders = () => this.escapedMessage().match(tagPattern) || [];

    this.listPlaceholdersWithoutBrackets = () => this.listPlaceholders().map(
      placeholder => placeholder.substring(2, placeholder.length - 2)
    );

    this.replacePlaceholders = () => this.$backgroundMaskForeground.html(
      this.escapedMessage().replace(
        tagPattern, match => `<span class='tag'>${match}</span>`
      )
    );

    this.hint = () => this.$placeHolderHint.html(
      getPlaceholderHint(this.listPlaceholdersWithoutBrackets())
    );

    this.update = () => (
      this.replacePlaceholders() && this.resize() && this.hint()
    );

    this.demo = () => (
      this.$textbox.val((i, current) => `Dear ((name)), ${current}`) && this.update()
    );

  };

})(window.GOVUK.Modules);
