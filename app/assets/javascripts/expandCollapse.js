(function(Modules) {
  "use strict";

  Modules.ExpandCollapse = function() {

    this.start = function(component) {

      this.$component = $(component);

      this.$toggle = this.$component.find('.toggle')
        .on(
          "click",
          this.change
        )
        .on("keydown", this.filterKeyPresses([32, 13], this.change));

      if (this.getNativeHeight() < this.$component.data('max-height')) {
        this.change();
      }

    };

    this.filterKeyPresses = (keys, callback) => function(event) {

      if (keys.indexOf(event.keyCode)) return;

      event.preventDefault();
      callback();

    };

    this.getNativeHeight = function() {

      var $copy = this.$component.clone().css({
        'position': 'absolute',
        'left': '9999px',
        'width': this.$component.width(),
        'font-size': this.$component.css('font-size'),
        'line-height': this.$component.css('line-height')
      }).addClass('expanded');

      $('body').append($copy);

      var nativeHeight = $copy.height();

      $copy.remove();

      return nativeHeight;

    };

    this.change = () => this.toggleCollapsed() && this.$toggle.remove();

    this.toggleCollapsed = () => this.$component.addClass('expanded');

  };

})(window.GOVUK.Modules);
