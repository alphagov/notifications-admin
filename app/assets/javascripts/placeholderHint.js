(function(Modules) {
  "use strict";

  if (
    !('oninput' in document.createElement('input'))
  ) return;

  const tagPattern = /\(\([^\)\(]+\)\)/g;

  Modules.PlaceholderHint = function() {

    this.start = function(component) {

      this.$component = $(component);
      this.originalHTML = this.$component.html();
      this.$allTextboxes = $(this.$component.data('textboxes-selector'));
      this.$targetTextbox = $(this.$component.data('target-textbox-selector'));

      this.$component
        .on('click', '.placeholder-hint-action', this.demo);
      
      this.$allTextboxes
        .on('input', this.hint)
        .trigger('input');

    };

    this.getPlaceholderHint = function() {

      let placeholders = this.listPlaceholdersWithoutBrackets();

      if (0 === placeholders.length) {
        return `
          ${this.originalHTML}
          <span class='placeholder-hint-action' tabindex='0' role='button'>Show me how</span>
        `;
      }
      if (1 === placeholders.length) {
          return `
            ${this.originalHTML}
            <p>You’ll populate the ‘${placeholders[0]}’ field when you send messages using this template</p>
          `;
      }    
      return `
        ${this.originalHTML}
        <p>You’ll populate your fields when you send some messages</p>
      `;

    };

    this.escapedMessages = () => $('<div/>').text(
      this.$allTextboxes.map(function() {
          return $(this).val();
      }).get()
    ).html();

    this.listPlaceholders = () => this.escapedMessages().match(tagPattern) || [];

    this.listPlaceholdersWithoutBrackets = () => this.listPlaceholders().map(
      placeholder => placeholder.substring(2, placeholder.length - 2)
    );

    this.renderDemo = () => this.$targetTextbox.val((i, current) => `Dear ((name)), ${current}`);

    this.hint = () => this.$component.html(
      this.getPlaceholderHint()
    );

    this.demo = () => (
      this.renderDemo() && this.$targetTextbox.trigger('input') && this.hint()
    );

  };

})(window.GOVUK.Modules);
