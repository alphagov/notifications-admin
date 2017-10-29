(function(Modules) {
  "use strict";

  Modules.FullscreenTable = function() {

    this.start = function(component) {

      this.$component = $(component);
      this.nativeHeight = this.$component.innerHeight();
      this.topOffset = this.$component.offset().top;

      this.insertShim();
      this.maintainHeight();

      $(window).on('scroll resize', this.maintainHeight);

      if (
        window.GOVUK.stopScrollingAtFooter &&
        window.GOVUK.stopScrollingAtFooter.updateFooterTop
      ) {
        window.GOVUK.stopScrollingAtFooter.updateFooterTop();
      }

    };

    this.insertShim = () => this.$component.after(
      $("<div class='fullscreen-shim'/>").css({
        'height': this.nativeHeight - this.topOffset,
        'top': this.topOffset
      })
    );

    this.maintainHeight = () => this.$component.css({
      'max-height': Math.min(
        $(window).height() - this.topOffset + $('html, body').scrollTop(),
        this.nativeHeight
      ),
      'min-height': $(window).height() - this.topOffset
    });

  };

})(window.GOVUK.Modules);
