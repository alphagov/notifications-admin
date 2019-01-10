;(function (global) {
  'use strict';

  var $ = global.jQuery;
  var GOVUK = global.GOVUK || {};
  var _mode = 'default';

  // Constructor for objects holding data for each element to have sticky behaviour
  var StickyElement = function ($el, sticky) {
    this._sticky = sticky;
    this.$fixedEl = $el;
    this._initialFixedClass = 'content-fixed-onload';
    this._fixedClass = 'content-fixed';
    this._appliedClass = null;
    this._$shim = null;
    this._stopped = false;
    this._canBeStuck = true;
  };
  StickyElement.prototype.stickyClass = function () {
    return (this._sticky._initialPositionsSet) ? this._fixedClass : this._initialFixedClass;
  };
  StickyElement.prototype.appliedClass = function () {
    return this._appliedClass;
  };
  StickyElement.prototype.removeStickyClasses = function () {
    this.$fixedEl.removeClass([this._initialFixedClass, this._fixedClass].join(' '));
  };
  StickyElement.prototype.isStuck = function () {
    return this._appliedClass !== null;
  };
  StickyElement.prototype.stick = function () {
    this._appliedClass = this.stickyClass();
    this.$fixedEl.addClass(this._appliedClass);
    this._hasBeenCalled = true;
  };
  StickyElement.prototype.release = function () {
    this._appliedClass = null;
    this._hasBeenCalled = true;
  };
  // When a sticky element is moved into the 'stuck' state, a shim is inserted into the
  // page to preserve the space the element occupies in the flow.
  StickyElement.prototype.addShim = function (position) {
    this._$shim = $('<div class="shim" style="width: ' + this.horizontalSpace + 'px; height: ' + this.inPageVerticalSpace + 'px">&nbsp</div>');
    this.$fixedEl[position](this._$shim);
  };
  StickyElement.prototype.removeShim = function () {
    if (this._$shim !== null) {
      this._$shim.remove();
      this._$shim = null;
    }
  };
  // Changes to the dimensions of a sticky element with a shim need to be passed on to the shim
  StickyElement.prototype.updateShim = function () {
    if (this._$shim) {
      this._$shim.css({
        'height': this.inPageVerticalSpace,
        'width': this.horizontalSpace
      });
    }
  };
  StickyElement.prototype.stop = function () {
    this._stopped = true;
  };
  StickyElement.prototype.unstop = function () {
    this._stopped = false;
  };
  StickyElement.prototype.isStopped = function () {
    return this._stopped;
  };
  StickyElement.prototype.isInPage = function () {
    var node = this.$fixedEl.get(0);

    return (node === document.body) ? false : document.body.contains(node);
  };
  StickyElement.prototype.canBeStuck = function (val) {
    if (val !== undefined) {
      this._canBeStuck = val;
    } else {
      return this._canBeStuck;
    }
  };
  StickyElement.prototype.hasLoaded = function (val) {
    if (val !== undefined) {
      this._hasLoaded = val;
    } else {
      return this._hasLoaded;
    }
  };

  // Object collecting together methods for treating sticky elements as if they
  // were wrapped by a dialog component
  var dialog = {
    _hasResized: false,
    _getTotalHeight: function (els) {
      var reducer = function (accumulator, currentValue) {
        return accumulator + currentValue;
      };
      return $.map(els, function (el) { return el.height; }).reduce(reducer);
    },
    _elsThatCanBeStuck: function (els) {
      return $.grep(els, function (el) { return el.canBeStuck(); });
    },
    hasOppositeEdge: function (el, sticky) {
      var els = this._elsThatCanBeStuck(sticky._els);
      var idx;
      
      if (els.length < 2) { return true; }

      idx = els.indexOf(el);

      return (sticky.edge === 'top') ? idx === (els.length - 1) : idx === 0;
    },
    getOffsetFromEdge: function (el, sticky) {
      var els = this._elsThatCanBeStuck(sticky._els).slice();
      var elIdx;

      // els must be arranged furtherest from window edge is stuck to first
      // default direction is order in document
      if (sticky.edge === 'top') {
        els.reverse();
      }

      elIdx = els.indexOf(el);

      // if next to window edge the dialog is stuck to, no offset
      if (elIdx === (els.length - 1)) { return 0; }

      // get all els between this one and the window edge
      els = els.slice(elIdx + 1);

      return this._getTotalHeight(els);
    },
    getOffsetFromEnd: function (el, sticky) {
      var els = this._elsThatCanBeStuck(sticky._els).slice();
      var elIdx;

      // els must be arranged furtherest from window edge is stuck to first
      // default direction is order in document
      if (sticky.edge === 'bottom') {
        els.reverse();
      }

      elIdx = els.indexOf(el);

      // if next to opposite edge to the one the dialog is stuck to, no offset
      if (elIdx === (els.length - 1)) { return 0; }

      // get all els between this one and the opposite edge
      els = els.slice(elIdx + 1);

      return this._getTotalHeight(els);
    },
    // checks total height of all this._sticky elements against a height
    // unsticks each that won't fit and marks them as unstickable
    fitToHeight: function (sticky) {
      var self = this;
      var els = sticky._els.slice();
      var height = sticky.getWindowDimensions().height;
      var elsThatCanBeStuck = function () {
        return $.grep(els, function (el) { return el.canBeStuck(); });
      };
      var totalStickyHeight = function () {
        return self._getTotalHeight(elsThatCanBeStuck());
      };
      var dialogFitsHeight = function () {
        return totalStickyHeight() <= height;
      };

      // els must be arranged furtherest from window edge is stuck to first
      // default direction is order in document
      if (sticky.edge === 'top') {
        els.reverse();
      }

      // reset elements
      $.each(els, function (i, el) { el.canBeStuck(true); });

      while (elsThatCanBeStuck().length && !dialogFitsHeight()) {
        var currentEl = elsThatCanBeStuck()[0];

        sticky.reset(currentEl);
        currentEl.canBeStuck(false);

        if (!sticky._hasResized) { sticky._hasResized = true; }
      }

      return this._getTotalHeight(els);
    },
    getInPageEdgePosition: function (sticky) {
      var idx = (sticky.edge === 'top') ? 0 : sticky._els.length - 1;

      return sticky._els[idx].inPageEdgePosition;
    },
    getHeight: function (els) {
      return this._getTotalHeight(this._elsThatCanBeStuck(els));
    },
    adjustForResize: function (sticky) {
      var windowHeight = sticky.getWindowDimensions().height;

      if (sticky.edge === 'top') {
        $(window).scrollTop(this.getInPageEdgePosition(sticky));
      } else {
        $(window).scrollTop(this.getInPageEdgePosition(sticky) - windowHeight);
      }

      sticky._hasResized = false;
    },
    releaseEl: function (el, sticky) {
      el.$fixedEl.css(sticky.edge, '');
    }
  };

  // Constructor for objects collecting together all generic behaviour for controlling the state of
  // sticky elements
  var Sticky = function (selector) {
    this._hasScrolled = false;
    this._scrollTimeout = false;
    this._hasResized = false;
    this._resizeTimeout = false;
    this._elsLoaded = false;
    this._initialPositionsSet = false;
    this._els = [];

    this.CSS_SELECTOR = selector;
    this.STOP_PADDING = 10;
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
  // Change state of sticky elements based on their position relative to the window
  Sticky.prototype.setElementPositions = function () {
    var self = this,
        windowDimensions = self.getWindowDimensions(),
        windowTop = self.getWindowPositions().scrollTop,
        windowPositions = {
          'top': windowTop,
          'bottom':  windowTop + windowDimensions.height
        };

    var _setElementPosition = function (el) {
      if (self.viewportIsWideEnough(windowDimensions.width)) {

        if (self.windowNotPastScrolledFrom(windowPositions, self.getScrolledFrom(el))) {
          self.reset(el);
        } else { // past the point it sits in the document
          if (self.windowNotPastScrollingTo(windowPositions, self.getScrollingTo(el))) {
            self.stick(el);
            if (el.isStopped()) {
              self.unstop(el);
            }
          } else { // window past scrollingTo position
            if (!el.isStuck()) {
              self.stick(el);
            }
            self.stop(el);
          }
        }

      } else {

        self.reset(el);

      }
    };

    $.each(self._els, function (i, el) {
      if (el.canBeStuck()) {
        _setElementPosition(el);
      }
    });

    if (self._initialPositionsSet === false) { self._initialPositionsSet = true; }
  };
  // Store all the dimensions for a sticky element to limit DOM queries
  Sticky.prototype.setElementDimensions = function (el, callback) {
    var self = this;
    var $el = el.$fixedEl;
    var onHeightSet = function () {
      // if element is shim'ed, pass changes in dimension on to the shim
      if (el._$shim) {
        el.updateShim();
      }
      if (callback !== undefined) {
        callback();
      }
    };

    this.setElWidth(el);
    this.setElHeight(el, onHeightSet);
  };
  // Reset element to original state in the page
  Sticky.prototype.reset = function (el) {
    if (el.isStopped()) {
      this.unstop(el);
    }
    if (el.isStuck()) {
      this.release(el);
    }
  };
  // Recalculate stored dimensions for all sticky elements
  Sticky.prototype.recalculate = function (opts) {
    var self = this;
    var onDimensionsSet = function () {
      if (_mode === 'dialog') {
        dialog.fitToHeight(self);
        dialog.adjustForResize(self);
      }
      self.setElementPositions();
    };

    if ((opts !== undefined) && ('mode' in opts)) { _mode = opts.mode; }

    $.each(self._els, function (i, el) {
      self.setElementDimensions(el, onDimensionsSet);
    });
  };
  Sticky.prototype.setElWidth = function (el) {
    var $el = el.$fixedEl;
    var width = $el.parent().width();

    el.horizontalSpace = width;
    // if stuck, element won't inherit width from parent so set explicitly
    if (el._$shim) {
      $el.width(width);
    }
  };
  Sticky.prototype.setElHeight = function (el, callback) {
    var self = this;
    var $el = el.$fixedEl;
    var $img = $el.find('img');

    if ((!self._elsLoaded) && ($img.length > 0)) {
      var image = new global.Image();
      image.onload = function () {
        el.inPageVerticalSpace = $el.outerHeight(true);
        el.height = $el.outerHeight();
        el.inPageEdgePosition = self.getInPageEdgePosition(el);
        callback();
      };
      image.src = $img.attr('src');
    } else {
      el.inPageVerticalSpace = $el.outerHeight(true);
      el.height = $el.outerHeight();
      el.inPageEdgePosition = self.getInPageEdgePosition(el);
      callback();
    }
  };
  Sticky.prototype.allElementsLoaded = function (totalEls) {
    return this._els.length === totalEls;
  };
  Sticky.prototype.hasEl = function (node) {
    return !!$.grep(this._els, function (el) { return el.$fixedEl.is(node); }).length;
  };
  Sticky.prototype.add = function (el, setPositions, cb) {
    var self = this;
    var $el = $(el);
    var elObj;

    // guard against adding elements already stored
    if (this.hasEl(el)) { return; }

    elObj= new StickyElement($el, self);

    self.setElementDimensions(elObj, function () {
      self._els.push(elObj);
      if (setPositions) {
        self.setElementPositions();
      }
      if (cb !== undefined) {
        cb();
      }
    });
  }; 
  Sticky.prototype.remove = function (el) {
    if ($.inArray(el, this._els) !== -1) {

      // reset DOM node to original state
      this.reset(el);

      // remove sticky element object
      this._els = $.grep(this._els, function (_el) { return _el !== el; });
    }
  };
  Sticky.prototype.init = function (opts) {
    var self = this;
    var $els = $(self.CSS_SELECTOR);
    var numOfEls = $els.length;
    var onAllLoaded = function () {
      if (self._els.length === numOfEls) {
        self._elsLoaded = true;
        self.endOfScrollArea = self.getEndOfScrollArea();

        // set positions based on initial scroll position
        self.setElementPositions();
      }
    };

    if ((opts !== undefined) && ('mode' in opts)) { _mode = opts.mode; }

    if (numOfEls > 0) {
      $els.each(function (i, el) {
        // delay setting position until all stickys are loaded
        self.add(el, false, onAllLoaded);
      });

      // flag when scrolling takes place and check (and re-position) sticky elements relative to
      // window position
      if (self._scrollTimeout === false) {
        $(global).scroll(function (e) { self.onScroll(); });
        self._scrollTimeout = global.setInterval(function (e) { self.checkScroll(); }, 50);
      }

      // Recalculate all dimensions when the window resizes
      if (self._resizeTimeout === false) {
        $(global).resize(function (e) { self.onResize(); });
        self._resizeTimeout = global.setInterval(function (e) { self.checkResize(); }, 50);
      }
    }
  };
  Sticky.prototype.viewportIsWideEnough = function (windowWidth) {
    return windowWidth > 768;
  };
  Sticky.prototype.onScroll = function () {
    this._hasScrolled = true;
  };
  Sticky.prototype.onResize = function () {
    this._hasResized = true;
  };
  Sticky.prototype.checkScroll = function () {
    var self = this;

    if (self._hasScrolled === true) {
      self._hasScrolled = false;
      self.setElementPositions();
    }
  };
  Sticky.prototype.checkResize = function () {
    var self = this,
        windowWidth = self.getWindowDimensions().width;

    if (self._hasResized === true) {
      self._hasResized = false;

      $.each(self._els, function (i, el) {
        if (!self.viewportIsWideEnough(windowWidth)) {
          self.reset(el);
        } else {
          self.setElementDimensions(el);
        }
      });

      if (self.viewportIsWideEnough(windowWidth)) {
        if (_mode === 'dialog') {
          dialog.fitToHeight(self);
          dialog.adjustForResize(self);
        }
        self.setElementPositions();
      }
    }
  };
  Sticky.prototype.release = function (el) {
    if (el.isStuck()) {
      var $el = el.$fixedEl;

      el.removeStickyClasses();
      $el.css('width', '');
      if (_mode === 'dialog') {
        dialog.releaseEl(el, this);
      }
      el.removeShim();
      el.release();
    }
  };

  // Extension of sticky object to add behaviours specific to sticking to top of window
  var stickAtTop = new Sticky('.js-stick-at-top-when-scrolling');
  stickAtTop.edge = 'top';
  // Store furthest point sticky elements are allowed
  stickAtTop.getEndOfScrollArea = function () {
    var footer = $('.js-footer:eq(0)');
    if (footer.length === 0) {
      return 0;
    }
    return footer.offset().top - this.STOP_PADDING;
  };
  // position of the bottom edge when in the page flow
  stickAtTop.getInPageEdgePosition = function (el) {
    return el.$fixedEl.offset().top;
  };
  stickAtTop.getScrolledFrom = function (el) {
    if (_mode === 'dialog') {
      return dialog.getInPageEdgePosition(this);
    } else {
      return el.inPageEdgePosition;
    }
  };
  stickAtTop.getScrollingTo = function (el) {
    var height = el.height;

    if (_mode === 'dialog') {
      height = dialog.getHeight(this._els);
    }

    return this.endOfScrollArea - height;
  };
  stickAtTop.getStoppingPosition = function (el) {
    var offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEnd(el, this);
    }

    return (this.endOfScrollArea - offset) - el.height;
  };
  stickAtTop.windowNotPastScrolledFrom = function (windowPositions, scrolledFrom) {
    return scrolledFrom > windowPositions.top;
  };
  stickAtTop.windowNotPastScrollingTo = function (windowPositions, scrollingTo) {
    return windowPositions.top < scrollingTo;
  };
  stickAtTop.stick = function (el) {
    if (!el.isStuck()) {
      var $el = el.$fixedEl;
      var offset = 0;

      if (_mode === 'dialog') {
        offset = dialog.getOffsetFromEdge(el, this);
      }

      el.addShim('before');
      $el.css({
        // element will be absolutely positioned so cannot rely on parent element for width
        'width': $el.width() + 'px',
        'top': offset + 'px'
      });
      el.stick();
    }
  };
  stickAtTop.stop = function (el) {
    if (!el.isStopped()) {
      el.$fixedEl.css({
        'position': 'absolute',
        'top': this.getStoppingPosition(el)
      });
      el.stop();
    }
  };
  stickAtTop.unstop = function (el) {
    el.$fixedEl.css({
      'position': '',
      'top': ''
    });
    el.unstop();
  };

  // Extension of sticky object to add behaviours specific to sticking to bottom of window
  var stickAtBottom = new Sticky('.js-stick-at-bottom-when-scrolling');
  stickAtBottom.edge = 'bottom';
  // Store furthest point sticky elements are allowed
  stickAtBottom.getEndOfScrollArea = function () {
    var header = $('.js-header:eq(0)');
    if (header.length === 0) {
      return 0;
    }
    return (header.offset().top + header.outerHeight()) + this.STOP_PADDING;
  };
  // position of the bottom edge when in the page flow
  stickAtBottom.getInPageEdgePosition = function (el) {
    return el.$fixedEl.offset().top + el.height;
  };
  stickAtBottom.getScrolledFrom = function (el) {
    if (_mode === 'dialog') {
      return dialog.getInPageEdgePosition(this);
    } else {
      return el.inPageEdgePosition;
    }
  };
  stickAtBottom.getScrollingTo = function (el) {
    var height = el.height;

    if (_mode === 'dialog') {
      height = dialog.getHeight(this._els);
    }

    return this.endOfScrollArea + height;
  };
  stickAtBottom.getStoppingPosition = function (el) {
    var offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEnd(el, this);
    }

    return this.endOfScrollArea + offset;
  };
  stickAtBottom.windowNotPastScrolledFrom = function (windowPositions, scrolledFrom) {
    return scrolledFrom < windowPositions.bottom;
  };
  stickAtBottom.windowNotPastScrollingTo = function (windowPositions, scrollingTo) {
    return windowPositions.bottom > scrollingTo;
  };
  stickAtBottom.stick = function (el) {
    if (!el.isStuck()) {
      var $el = el.$fixedEl;
      var offset = 0;

      if (_mode === 'dialog') {
        offset = dialog.getOffsetFromEdge(el, this);
      }

      el.addShim('after');
      $el.css({
        // element will be absolutely positioned so cannot rely on parent element for width
        'width': $el.width() + 'px',
        'bottom': offset + 'px'
      });
      el.stick();
    }
  };
  stickAtBottom.stop = function (el) {
    if (!el.isStopped()) {
      el.$fixedEl.css({
        'position': 'absolute',
        'top': this.getStoppingPosition(el),
        'bottom': 'auto'
      });
      el.stop();
    }
  };
  stickAtBottom.unstop = function (el) {
    var offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEdge(el, this);
    }

    el.$fixedEl.css({
      'position': '',
      'top': '',
      'bottom': offset + 'px'
    });
    el.unstop();
  };

  GOVUK.stickAtTopWhenScrolling = stickAtTop;
  GOVUK.stickAtBottomWhenScrolling = stickAtBottom;
  global.GOVUK = GOVUK;
})(window);
