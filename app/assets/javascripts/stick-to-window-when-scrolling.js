;(function (global) {
  'use strict';

  var $ = global.jQuery;
  var GOVUK = global.GOVUK || {};

  var StickyElement = function ($el, sticky) {
    this._sticky = sticky;
    this.$fixedEl = $el;
    this._initialFixedClass = 'content-fixed-onload';
    this._fixedClass = 'content-fixed';
    this._appliedClass = null;
    this._stopped = false;
    this.scrolledFrom = this._sticky.getScrolledFrom($el);
  };
  StickyElement.prototype.stickyClass = function () {
    return (this._sticky._initialPositionsSet) ? this._fixedClass : this._initialFixedClass;
  };
  StickyElement.prototype.appliedClass = function () {
    return this._appliedClass;
  };
  StickyElement.prototype.isStuck = function () {
    return this._appliedClass !== null;
  };
  StickyElement.prototype.stick = function () {
    this._appliedClass = this.stickyClass();
    this._hasBeenCalled = true;
  };
  StickyElement.prototype.release = function () {
    this._appliedClass = null;
    this._hasBeenCalled = true;
  };
  StickyElement.prototype.stop = function () {
    this._stopped = true;
  };
  StickyElement.prototype.unstop = function () {
    this._stopped = false;
  };

  // Stick elements to top of screen when you scroll past, documentation is in the README.md
  var Sticky = function (selector) {
    this._hasScrolled = false;
    this._scrollTimeout = false;
    this._hasResized = false;
    this._resizeTimeout = false;
    this._elsLoaded = false;
    this._initialPositionsSet = false;
    this._els = [];

    this.CSS_SELECTOR = selector;
  };
  Sticky.prototype.getWindowDimensions = function () {
    return {
      height: $(global).height(),
      width: $(global).width()
    };
  };
  Sticky.prototype.getWindowPositions = function () {
    return {
      scrollTop: $(global).scrollTop()
    };
  };
  Sticky.prototype.setElementPositions = function () {
    var self = this;

    $.each(self._els, function (i, el) {
      var $el = el.$fixedEl;

      var windowDimensions = self.getWindowDimensions();

      if (self.scrolledFromInsideWindow(el.scrolledFrom)) {
        self.release(el);
      } else {
        if (self.scrolledToOutsideWindow(el, windowDimensions.height)) {
          self.stop(el);
        } else if (self.viewportIsWideEnough(windowDimensions.width)) {
          if (el.stopped) {
            self.unstop(el);
          }
          self.stick(el);
        }
      }
    });

    if (self._initialPositionsSet === false) { self._initialPositionsSet = true; }
  };
  Sticky.prototype.setFixedTop = function (el) {
    var $siblingEl = $('<div></div>');
    $siblingEl.insertBefore(el.$fixedEl);
    var fixedTop = $siblingEl.offset().top - $siblingEl.position().top;
    $siblingEl.remove();

    el.fixedTop = fixedTop;
  };
  Sticky.prototype.setElHeight = function (el) {
    var self = this;
    var fixedOffset = parseInt(el.$fixedEl.css('top'), 10);
    var $el = el.$fixedEl;
    var $img = $el.find('img');

    fixedOffset = isNaN(fixedOffset) ? 0 : fixedOffset;

    if ((!self._elsLoaded) && ($img.length > 0)) {
      var image = new global.Image();
      image.onload = function () {
        el.height = $el.outerHeight() + fixedOffset;
        el.scrolledTo = self.getScrollingTo(el);
        self.checkElementsLoaded();
      };
      image.src = $img.attr('src');
    } else {
      el.height = $el.outerHeight() + fixedOffset;
      el.scrolledTo = self.getScrollingTo(el);
      self.checkElementsLoaded();
    }
  };
  Sticky.prototype.checkElementsLoaded = function () {
    this._elsLoaded = $.grep(this._els, function (el) { return ('height' in el); }).length === this._els.length;
  };
  Sticky.prototype.init = function () {
    var self = this;
    var $els = $(self.CSS_SELECTOR);

    if ($els.length > 0) {
      $els.each(function (i, el) {
        var $el = $(el);
        var elObj = new StickyElement($el, self);

        self.setFixedTop(elObj);
        self.setElHeight(elObj);
        self._els.push(elObj);
      });

      // set element positions based on page scroll position on load
      self.setElementPositions();

      if (self._scrollTimeout === false) {
        $(global).scroll(function (e) { self.onScroll(); });
        self._scrollTimeout = global.setInterval(function (e) { self.checkScroll(); }, 50);
      }

      if (self._resizeTimeout === false) {
        $(global).resize(function (e) { self.onResize(); });
        self._resizeTimeout = global.setInterval(function (e) { self.checkResize(); }, 50);
      }
    }
  };
  Sticky.prototype.onScroll = function () {
    this._hasScrolled = true;
  };
  Sticky.prototype.onResize = function () {
    this._hasResized = true;
  };
  Sticky.prototype.viewportIsWideEnough = function (windowWidth) {
    return windowWidth > 768;
  };
  Sticky.prototype.checkScroll = function () {
    var self = this;

    if (self._hasScrolled === true) {
      self._hasScrolled = false;
      self.setElementPositions(true);
    }
  };
  Sticky.prototype.checkResize = function () {
    var self = this;

    if (self._hasResized === true) {
      self._hasResized = false;

      var windowDimensions = self.getWindowDimensions();

      $.each(self._els, function (i, el) {
        var $el = el.$fixedEl;

        var elResize = $el.hasClass('js-self-resize');
        if (elResize) {
          var $shim = $('.shim');
          var $elParent = $el.parent('div');
          var elParentWidth = $elParent.width();
          $shim.css('width', elParentWidth);
          $el.css('width', elParentWidth);
          self.setElHeight(el);
        }

        if (!self.viewportIsWideEnough(windowDimensions.width)) {
          self.release($el);
        }
      });
    }
  };
  Sticky.prototype.stick = function (el) {
    if (!el.isStuck()) {
      var $el = el.$fixedEl;
      var height = Math.max($el.height(), 1);
      var width = $el.width();

      this.addShimForEl($el, width, height);
      $el.css('width', width + 'px').addClass(el.stickyClass());
      el.stick();
    }
  };
  Sticky.prototype.release = function (el) {
    if (el.isStuck()) {
      var $el = el.$fixedEl;

      $el.removeClass(el.appliedClass()).css('width', '');
      $el.siblings('.shim').remove();
      el.release();
    }
  };

  var stickAtTop = new Sticky('.js-stick-at-top-when-scrolling');
  stickAtTop.getScrolledFrom = function ($el) {
    return $el.offset().top;
  };
  stickAtTop.getScrollingTo = function (el) {
    var footer = $('.js-footer:eq(0)');
    if (footer.length === 0) {
      return 0;
    }
    return (footer.offset().top - 10) - el.height;
  };
  stickAtTop.scrolledFromInsideWindow = function (scrolledFrom) {
    var windowTop = this.getWindowPositions().scrollTop;

    return scrolledFrom > windowTop;
  };
  stickAtTop.scrolledToOutsideWindow = function (el, windowHeight) {
    var windowTop = this.getWindowPositions().scrollTop;
  
    return windowTop > el.scrolledTo;
  };
  stickAtTop.addShimForEl = function ($el, width, height) {
    $el.before('<div class="shim" style="width: ' + width + 'px height: ' + height + 'px">&nbsp</div>');
  };
  stickAtTop.stop = function (el) {
    if (!el.stopped()) {
      el.$fixedEl.css({ 'position': 'absolute', 'top': el.scrolledTo });
      el.stop();
    }
  };
  stickAtTop.unstop = function (el) {
    if (el.stopped()) {
      el.$fixedEl.css({ 'position': '', 'top': '' });
      el.unstop();
    }
  };

  var stickAtBottom = new Sticky('.js-stick-at-bottom-when-scrolling');
  stickAtBottom.getScrolledFrom = function ($el) {
    return $el.offset().top + $el.outerHeight();
  };
  stickAtBottom.getScrollingTo = function (el) {
    var header = $('.js-header:eq(0)');
    if (header.length === 0) {
      return 0;
    }
    return (header.offset().top + header.outerHeight() + 10) + el.height;
  };
  stickAtBottom.scrolledFromInsideWindow = function (scrolledFrom) {
    var windowBottom = this.getWindowPositions().scrollTop + this.getWindowDimensions().height;

    return scrolledFrom < windowBottom;
  };
  stickAtBottom.scrolledToOutsideWindow = function (el, windowHeight) {
    var windowBottom = this.getWindowPositions().scrollTop + this.getWindowDimensions().height;

    return windowBottom < el.scrolledTo;
  };
  stickAtBottom.addShimForEl = function ($el, width, height) {
    $el.after('<div class="shim" style="width: ' + width + 'px height: ' + height + 'px">&nbsp</div>');
  };
  stickAtBottom.stop = function (el) {
    if (!el.stopped()) {
      el.$fixedEl.css({
        'position': 'absolute',
        'top': (el.scrolledTo - el.height),
        'bottom': 'auto'
      });
      el.stop();
    }
  };
  stickAtBottom.unstop = function (el) {
    if (el.stopped()) {
      el.$fixedEl.css({
        'position': '',
        'top': '',
        'bottom': ''
      });
      el.unstop();
    }
  };

  GOVUK.stickAtTopWhenScrolling = stickAtTop;
  GOVUK.stickAtBottomWhenScrolling = stickAtBottom;
  global.GOVUK = GOVUK;
})(window);
