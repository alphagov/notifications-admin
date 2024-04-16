(function(Modules) {
  "use strict";

  Modules.FullscreenTable = function() {

    this.start = function(component) {

      this.$component = $(component);
      this.$table = this.$component.find('table');
      this.nativeHeight = this.$component.innerHeight() + 20; // 20px to allow room for scrollbar
      this.topOffset = this.$component.offset().top;

      this.insertShims();
      this.maintainWidth();
      this.maintainHeight();
      this.toggleShadows();

      $(window)
        .on('scroll resize', this.maintainHeight)
        .on('resize', this.maintainWidth);

      this.$scrollableTable
        .on('scroll', this.toggleShadows)
        .on('scroll', this.maintainHeight)
        .on('focus blur', () => this.$component.toggleClass('js-focus-style'));

      if (
        window.GOVUK.stickAtBottomWhenScrolling &&
        window.GOVUK.stickAtBottomWhenScrolling.recalculate
      ) {
        window.GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

      this.maintainWidth();

    };

    this.insertShims = () => {

      const attributesForFocus = 'role aria-labelledby tabindex';
      let captionId = this.$table.find('caption').text().toLowerCase().replace(/[^A-Za-z]+/g, '');

      this.$table.find('caption').attr('id', captionId);
      this.$table.wrap(`<div class="fullscreen-scrollable-table" role="region" aria-labelledby="${captionId}" tabindex="0"/>`);

      this.$component
        .append(
          this.$component.find('.fullscreen-scrollable-table')
            .clone()
            .addClass('fullscreen-fixed-table')
            .removeClass('fullscreen-scrollable-table')
            .removeAttr(attributesForFocus)
            .attr('aria-hidden', true)
            .find('caption')
            .removeAttr('id')
            .closest('.fullscreen-fixed-table')
        )
        .append(
          '<div class="fullscreen-right-shadow" />'
        )
        .after(
          $("<div class='fullscreen-shim'/>").css({
            'height': this.nativeHeight,
            'top': this.topOffset
          })
        )
        .css('position', 'absolute');

      this.$scrollableTable = this.$component.find('.fullscreen-scrollable-table');
      this.$fixedTable = this.$component.find('.fullscreen-fixed-table');

    };

    this.maintainHeight = () => {

      let height = Math.min(
        $(window).height() - this.topOffset + $(window).scrollTop(),
        this.nativeHeight
      );

      this.$scrollableTable.outerHeight(height);
      this.$fixedTable.outerHeight(height);

    };

    this.maintainWidth = () => {

      const $scrollableIndexColumnHeader = this.$scrollableTable.find('.table-field-heading-first').eq(0);
      const $fixedIndexColumnHeader = this.$fixedTable.find('.table-field-heading-first').eq(0);

      this.$scrollableTable
        .css({
          'width': this.$component.parent().width()
        });

      // The table layout algorithm can sometimes work differently on the two tables, because they are
      // positioned differently. This results in both versions of the index column having different widths.
      // If this happens, set both by the width of the fixed column.
      if ($fixedIndexColumnHeader.width() !== $scrollableIndexColumnHeader.width()) {
        $scrollableIndexColumnHeader.css({
          'width': $fixedIndexColumnHeader.width()
        });
      }

      // The fixed table container is positioned absolutely to needs a width set explicity
      this.$fixedTable
        .css({
          'width': $fixedIndexColumnHeader.outerWidth() + 4 // allow 4px space for the shadow
        });

    };

    this.toggleShadows = () => {

      this.$fixedTable
        .toggleClass(
          'fullscreen-scrolled-table',
          this.$scrollableTable.scrollLeft() > 0
        );

      this.$component.find('.fullscreen-right-shadow')
        .toggleClass(
          'visible',
          this.$scrollableTable.scrollLeft() < (this.$table.width() - this.$scrollableTable.width())
        );

      setTimeout(
        () => this.$component.find('.fullscreen-right-shadow').addClass('with-transition'),
        3000
      );

    };

  };

})(window.GOVUK.NotifyModules);
