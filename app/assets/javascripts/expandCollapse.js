(function(Modules) {
  "use strict";

  Modules.ExpandCollapse = function() {

    this.start = function(component) {

      this.$component = $(component)
        .append(`
          <div class='toggle' tabindex='0'>...<span class='visually-hidden'>show full email</span></div>
        `)
        .addClass('collapsed');

      this.$toggle = this.$component.find('.toggle');

      this.$toggle
        .on(
          "click",
          ".toggle",
          this.change
        )
        .on("keydown", this.filterKeyPresses([32, 13], this.change));

    };

    this.filterKeyPresses = (keys, callback) => function(event) {

      if (keys.indexOf(event.keyCode)) return;

      event.preventDefault();
      callback();

    };

    this.change = () => this.toggleCollapsed() && this.$toggle.remove();

    this.toggleCollapsed = () => this.$component.toggleClass('collapsed');

  };

})(window.GOVUK.Modules);
