import { offset } from './utils.mjs';
import { Caret } from 'textarea-caret-ts';

let _mode = 'default';

// Constructor to make objects representing the area sticky elements can scroll in
class ScrollArea {

  constructor (el, edge, selector) {
    const $el = el.$fixedEl;
    let $scrollArea = $el.closest('.sticky-scroll-area');

    if ($scrollArea === null) {
      $scrollArea = $el.parentElement;
      $scrollArea.classList.add('sticky-scroll-area');
    }
    this._els = [el];
    this.edge = edge;
    this.selector = selector;
    this.node = $scrollArea;
    this.setEvents();
  }

  addEl (el) {
    this._els.push(el);
  }

  hasEl (el) {
    return this._els.includes(el);
  }

  updateEls (usedEls) {
    this._els = usedEls;
  }

  #keyUpHandler (e) {
    if (e.target.matches('textarea')) {
      this.focusHandler(e);
    }
  }

  setEvents () {
    this.node.addEventListener('focus', this.focusHandler.bind(this), { capture: true, passive: true });
    this.node.addEventListener('keyup', this.#keyUpHandler.bind(this), { passive: true });
  }

  removeEvents () {
    this.node.removeEventListener('focus', this.focusHandler.bind(this), { capture: true, passive: true });
    this.node.removeEventListener('keyup', this.#keyUpHandler.bind(this), { passive: true });
  }

  getFocusedDetails = {
    forElement: ($focusedElement) => {
      const focused = {
        'top': offset($focusedElement).top,
        'height': $focusedElement.offsetHeight,
        'type': 'element'
      };
      focused.bottom = focused.top + focused.height;

      return focused;
    },
    forCaret: ($textarea) => {
      const textarea = $textarea;
      const caretCoordinates = Caret.getAbsolutePosition(textarea);
      const focused = {
        'top': caretCoordinates.top,
        'height': caretCoordinates.height,
        'type': 'caret'
      };
      focused.bottom = focused.top + focused.height;

      return focused;
    }
  };

  focusHandler () {
    this.scrollToRevealElement(document.activeElement);
  }

  scrollToRevealElement ($el) {
    const nodeName = $el.nodeName.toLowerCase();
    const nodeType = $el.getAttribute('type');
    const endOfFurthestEl = focusOverlap.endOfFurthestEl(this._els, this.edge);
    const isInSticky = $el.closest(this.selector) !== null;
    let focused;
    let overlap;

    if (nodeName === 'textarea') {
      focused = this.getFocusedDetails.forCaret($el);
    } else if (!isInSticky && (nodeType === 'checkbox' || nodeType === 'radio')) {
      focused = this.getFocusedDetails.forElement($el.parentElement);
    } else {
      if (isInSticky) { return; }
      focused = this.getFocusedDetails.forElement($el);
    }

    overlap = focusOverlap.getOverlap(focused, this.edge, endOfFurthestEl);
    if (overlap > 0) {
      focusOverlap.adjustForOverlap(focused, this.edge, overlap);
    }
  }

  destroy () {
    this.removeEvents();
  }

}

// Singleton class for interacting with scrollareas
class ScrollAreas {
  #scrollAreas = [];

  constructor () {}

  getAreaForEl (el) {
    let loopIdx = this.#scrollAreas.length;

    while(loopIdx--) {
      if (this.#scrollAreas[loopIdx].hasEl(el)) {
        return this.#scrollAreas[loopIdx];
      }
    }

    return false;
  }

  getAreaByEl (el) {
    const matches = this.#scrollAreas.filter(area => area._els.includes(el));

    return matches[0] || false;
  }

  addEl (el, edge, selector) {
    const scrollArea = this.getAreaForEl(el);

    if (!scrollArea) {
      this.#scrollAreas.push(new ScrollArea(el, edge, selector));
    } else {
      scrollArea.addEl(el);
    }
  }

  syncEls (elsInDOM) {
    const unusedAreas = [];

    const getUsed = (area) => {
      return elsInDOM.filter(el => area.hasEl(el));
    };

    const deleteUnused = (idx, areaIdx) => {
      // remove any events for overlap checking bound to the scrollArea
      this.#scrollAreas[areaIdx].destroy();
      this.#scrollAreas.splice(areaIdx, 1);
    };

    // update any scroll areas with els still in the DOM and track any with none
    this.#scrollAreas.forEach((area, areaIdx) => {
      const used = getUsed(area);

      if (!used.length) {
        unusedAreas.push(areaIdx);
      }

      area.updateEls(used);
    });

    // delete any scroll areas with no els still in DOM
    unusedAreas.forEach(deleteUnused);
  }

  filterBy (filterFunc) {
    return this.#scrollAreas.filter(filterFunc);
  }

}
const scrollAreas = new ScrollAreas();

// Object collecting together methods for stopping sticky overlapping focused elements
const focusOverlap = {
  getOverlap: function (focused, edge, endOfFurthestEl) {
    if (!endOfFurthestEl) { return 0; }

    if (edge === 'top') {
      return endOfFurthestEl - focused.top;
    } else {
      return focused.bottom - endOfFurthestEl;
    }
  },
  endOfFurthestEl: function (els, edge) {
    const stuckEls = els.filter((el) => el.isStuck());
    let edgeOfEl;

    if (!stuckEls.length) { return false; }

    if (edge === 'bottom') {
      edgeOfEl = el => offset(el.$fixedEl).top;
    } else {
      edgeOfEl = el => offset(el.$fixedEl).top + el.height;
    }

    const offsets = stuckEls.map((el) => edgeOfEl(el));

    return offsets.reduce((accumulator, offset) => {
      return (accumulator < offset) ? offset: accumulator;
    });
  },
  adjustForOverlap: function (focused, edge, overlap) {
    const scrollTop = window.scrollY;

    // scroll so element becomes visible
    if (edge === 'top') {
      window.scrollTo(window.pageXOffset, (scrollTop - overlap));
    } else {
      window.scrollTo(window.pageXOffset, (scrollTop + overlap));
    }
  }
};

// Singleton class for dealing with marking the edge of a sticky, or group of sticky elements (as seen in dialog mode)
class OppositeEdge {

  #classes = {
    'top': 'content-fixed__top',
    'bottom': 'content-fixed__bottom'
  };

  constructor () {}

  mark (sticky) {
    const edgeClass = this.#classes[sticky.edge];
    let els;

    if (_mode === 'dialog') {
      els = [dialog.getElementAtOppositeEnd(sticky)];
    } else {
      els = sticky._els;
    }

    els = els.filter((el) => el.isStuck());

    els.forEach((el) => el.$fixedEl.classList.add(edgeClass));
  }

  unmark (sticky) {
    const edgeClass = this.#classes[sticky.edge];

    sticky._els.forEach(el => el.$fixedEl.classList.remove(edgeClass));
  }

}
const oppositeEdge = new OppositeEdge();


// Constructor for objects holding data for each element to have sticky behaviour
var StickyElement = function ($el, sticky) {
  this._sticky = sticky;
  this.$fixedEl = $el;
  this._initialFixedClass = 'content-fixed-onload';
  this._fixedClass = 'content-fixed';
  this._appliedClass = null;
  this._$shim = null;
  this._stopped = false;
  this._hasLoaded = false;
  this._canBeStuck = true;
  this.verticalMargins = {
    'top': parseInt(this.$fixedEl.css('margin-top'), 10),
    'bottom': parseInt(this.$fixedEl.css('margin-bottom'), 10),
  };
};
StickyElement.prototype._getShimCSS = function () {
  return {
    'width': this.horizontalSpace + 'px',
    'height': this.height + 'px',
    'margin-top': this.verticalMargins.top + 'px',
    'margin-bottom': this.verticalMargins.bottom + 'px'
  };
};
StickyElement.prototype.stickyClass = function () {
  return (this._sticky.initialPositionsSet) ? this._fixedClass : this._initialFixedClass;
};
StickyElement.prototype.appliedClass = function () {
  return this._appliedClass;
};
StickyElement.prototype.removeStickyClasses = function (sticky) {
  this.$fixedEl.removeClass([
    this._initialFixedClass,
    this._fixedClass
  ].join(' '));
};
StickyElement.prototype.isStuck = function () {
  return this._appliedClass !== null;
};
StickyElement.prototype.stick = function (sticky) {
  this._appliedClass = this.stickyClass();
  this.$fixedEl.addClass(this._appliedClass);
  this._hasBeenCalled = true;
};
StickyElement.prototype.release = function (sticky) {
  this._appliedClass = null;
  this.removeStickyClasses(sticky);
  this._hasBeenCalled = true;
};
// When a sticky element is moved into the 'stuck' state, a shim is inserted into the
// page to preserve the space the element occupies in the flow.
StickyElement.prototype.addShim = function (position) {
  this._$shim = $('<div class="shim">&nbsp</div>');
  this._$shim.css(this._getShimCSS());
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
    this._$shim.css(this._getShimCSS());
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
  hasResized: false,
  spaceBetweenStickys: 40,
  // we add padding of 20px around each sticky to give some space between it and the rest of the page
  // this shouldn't apply between stickys in a stack
  // (the in-page CSS handles this by each subsequent sticky in a sequence having margin: -40px)
  _getPaddingBetweenEls: function (els) {
    if (els.length <= 1) { return 0; }

    return (els.length - 1) * this.spaceBetweenStickys;
  },
  _getTotalHeight: function (els) {
    var reducer = function (accumulator, currentValue) {
      return accumulator + currentValue;
    };
    var combinedHeight = $.map(els, function (el) { return el.height; }).reduce(reducer);

    return combinedHeight - this._getPaddingBetweenEls(els);
  },
  _elsThatCanBeStuck: function (els) {
    return $.grep(els, function (el) { return el.canBeStuck(); });
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

    // make els all those from this one to the window edge
    els = els.slice(elIdx + 1);

    // remove the space between those els and the one on the edge
    return this._getTotalHeight(els) - this.spaceBetweenStickys;
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

    // make els all those from this one to the window edge
    els = els.slice(elIdx + 1);

    return this._getTotalHeight(els) - this.spaceBetweenStickys;
  },
  // checks total height of all this._sticky elements against a height
  // unsticks each that won't fit and marks them as unstickable
  fitToHeight: function (sticky) {
    var self = this;
    var els = sticky._els.slice();
    var height = Sticky.getWindowDimensions().height;
    var totalStickyHeight = function () {
      return self._getTotalHeight(self._elsThatCanBeStuck(els));
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

    while (self._elsThatCanBeStuck(els).length && !dialogFitsHeight()) {
      var currentEl = self._elsThatCanBeStuck(els)[0];

      sticky.reset(currentEl);
      currentEl.canBeStuck(false);

      if (!self.hasResized) { self.hasResized = true; }
    }
  },
  getElementAtStickyEdge: function (sticky) {
    var els = this._elsThatCanBeStuck(sticky._els);
    var idx = (sticky.edge === 'top') ? 0 : els.length - 1;

    return els[idx];
  },
  // get element at the end opposite the sticky edge
  getElementAtOppositeEnd: function (sticky) {
    var els = this._elsThatCanBeStuck(sticky._els);
    var idx = (sticky.edge === 'top') ? els.length - 1 : 0;

    return els[idx];
  },
  getInPageEdgePosition: function (sticky) {
    return this.getElementAtStickyEdge(sticky).inPageEdgePosition;
  },
  getHeight: function (els) {
    return this._getTotalHeight(this._elsThatCanBeStuck(els));
  },
  adjustForResize: function (sticky) {
    var windowHeight = Sticky.getWindowDimensions().height;

    if (sticky.edge === 'top') {
      $(window).scrollTop(this.getInPageEdgePosition(sticky));
    } else {
      $(window).scrollTop(this.getInPageEdgePosition(sticky) - windowHeight);
    }

    this.hasResized = false;
  },
  releaseEl: function (el, sticky) {
    el.$fixedEl.css(sticky.edge, '');
  }
};

// Constructor for objects collecting together all generic behaviour for controlling the state of
// sticky elements
//
// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes
class Sticky {
  #hasScrolled = false;
  #scrollTimeout = false;
  #windowHasResized = false;
  #resizeTimeout = false;

  constructor (selector) {
    this._els = [];
    this.initialPositionsSet = false;

    this.CSS_SELECTOR = selector;
    this.STOP_PADDING = 10;
  }

  setMode (mode) {
    _mode = mode;
  }

  // Change state of sticky elements based on their position relative to the window
  setElementPositions () {
    const windowDimensions = Sticky.getWindowDimensions(),
          windowTop = Sticky.getWindowPositions().scrollTop,
          windowPositions = {
            'top': windowTop,
            'bottom':  windowTop + windowDimensions.height
          };

    const setElementPosition = (el) => {
      if (this.viewportIsWideEnough(windowDimensions.width)) {

        if (this.windowNotPastScrolledFrom(windowPositions, this.getScrolledFrom(el))) {
          this.reset(el);
        } else { // past the point it sits in the document
          if (this.windowNotPastScrollingTo(windowPositions, this.getScrollingTo(el))) {
            this.stick(el);
            if (el.isStopped) {
              this.unstop(el);
            }
          } else { // window past scrollingTo position
            if (!el.isStuck) {
              this.stick(el);
            }
            this.stop(el);
          }
        }

      } else {

        this.reset(el);

      }
    };

    // clean up any existing styles marking the edges of sticky elements
    oppositeEdge.unmark(this);

    this._els.forEach(el => {
      if (el.canBeStuck()) {
        setElementPosition(el);
      }
    });

    // add styles to mark the edge of sticky elements opposite to that stuck to the window
    oppositeEdge.mark(this);

    if (this.initialPositionsSet === false) { this.initialPositionsSet = true; }
  }

  // Store all the dimensions for a sticky element to limit DOM queries
  setElementDimensions (el, callback) {
    const onHeightSet = () => {
      // if element is shim'ed, pass changes in dimension on to the shim
      if (el.$shim) {
        el.updateShim();
      }
      if (callback !== undefined) {
        callback();
      }
    };

    this.setElWidth(el);
    this.setElHeight(el, onHeightSet);
  }

  // Reset element to original state in the page
  reset (el) {
    if (el.isStopped()) {
      this.unstop(el);
    }

    if (el.isStuck()) {
      this.release(el);
    }
  }

  // Recalculate stored dimensions for all sticky elements
  recalculate () {
    const onSyncComplete = () => {
      scrollAreas.syncEls(this._els);
      this.setEvents();
      if (_mode === 'dialog') {
        dialog.fitToHeight(this);
        if (dialog.hasResized) {
          dialog.adjustForResize(this);
        }
      }
      this.setElementPositions();
    };

    this.syncWithDOM(onSyncComplete);
  }

  // Public method to scroll so an element isn't covered by the sticky nav
  scrollToRevealElement ($el) {
    const scrollAreaNode = $el.closest('.sticky-scroll-area');
    const matches = scrollAreas.filterBy(scrollArea => {
      return scrollArea.node === scrollAreaNode;
    });

    if (matches.length) {
      matches[0].scrollToRevealElement($el);
    }
  }

  setElWidth (el) {
    const $el = el.$fixedEl;
    const scrollArea = scrollAreas.getAreaByEl(el);
    const width = scrollArea.node.getBoundingClientRect().width;

    el.horizontalSpace = width;

    // if stuck, element won't inherit width from parent so set explicitly
    if (el.$shim) {
      $el.style.width = width + 'px';
    }
  }

  setElHeight (el, callback) {
    const $el = el.$fixedEl;
    const $img = $el.querySelector('img');

    const onload = () => {
      el.height = $el.offsetHeight;
      // if element has a shim, the shim's offset represents the element's in-page position
      if (el.$shim) {
        el.inPageEdgePosition = this.getInPageEdgePosition(el.$shim);
      } else {
        el.inPageEdgePosition = this.getInPageEdgePosition($el);
      }
      callback();
    };

    if ((!el.hasLoaded()) && ($img !== null)) {
      const image = new window.Image();
      image.onload = () => {
        onload();
      };
      image.src = $img.attr('src');
    } else {
      onload();
    }
  }

  allElementsLoaded (totalEls) {
    return this._els.length === totalEls;
  }

  getElForNode (node) {
    const matches = this._els.filter(el => el.$fixedEl === node);

    return matches.length ? matches[0] : false;
  }

  add (node, setPositions, cb) {
    const $el = node;
    let elObj = this.getElForNode(node);
    const exists = !!elObj;

    const onDimensionsSet = () => {
      elObj.hasLoaded = true;

      // guard against adding elements already stored
      if (!exists) {
        this._els.push(elObj);
      }

      if (setPositions) {
        this.setElementPositions();
      }

      if (cb !== undefined) {
        cb();
      }
    };

    if (!exists) {
      elObj = new StickyElement($($el), this); // TODO: replace this use of $() when jQuery use is removed from StickyElement
      scrollAreas.addEl(elObj, this.edge, this.CSS_SELECTOR);
    }

    this.setElementDimensions(elObj, onDimensionsSet);
  }

  remove (el) {
    if (this._els.includes(el)) {

      // reset DOM node to original state
      this.reset(el);

      // remove sticky element object
      this._els = this._els.filter(_el => _el !== el);
    }
  }

  // gets all sticky elements in the DOM and removes any in this._els no longer in attached to it
  syncWithDOM (callback) {
    const $els = document.querySelectorAll(this.CSS_SELECTOR);
    const numOfEls = $els.length;

    const onLoaded = () => {
      if (this._els.length === numOfEls) {
        this.endOfScrollArea = this.getEndOfScrollArea();
        if (callback !== undefined) {
          callback();
        }
      }
    };

    // remove any els no longer in the DOM
    if (this._els.length) {
      this._els.forEach(el => {
        if (!el.isInPage()) {
          this.remove(el);
        }
      });
    }

    if (numOfEls) {
      // reset flag marking page load
      this.initialPositionsSet = false;

      $els.forEach(el => {
        // delay setting position until all stickys are loaded
        this.add(el, false, onLoaded);
      });
    }
  }

  init () {
    this.recalculate();
  }

  setEvents () {
    this._scrollEvent = this.onScroll.bind(this);
    this._resizeEvent = this.onResize.bind(this);

    // flag when scrolling takes place and check (and re-position) sticky elements relative to
    // window position
    if (this.#scrollTimeout === false) {
      // TODO: consider replacing with 'scrollEnd' event when more widely available
      // https://developer.mozilla.org/en-US/docs/Web/API/Document/scroll_event
      window.addEventListener('scroll', this._scrollEvent);
      this.#scrollTimeout = window.setInterval(this.checkScroll.bind(this), 50);
    }

    // Recalculate all dimensions when the window resizes
    if (this.#resizeTimeout === false) {
      window.addEventListener('resize', this._resizeEvent);
      this.#resizeTimeout = window.setInterval(this.checkResize.bind(this), 50);
    }
  }

  clearEvents () {
    if (this.#scrollTimeout !== false) {
      document.removeEventListener('scroll', this._scrollEvent);
      window.clearInterval(this.#scrollTimeout);
      this.#scrollTimeout = false;
    }

    if (this.#resizeTimeout !== false) {
      window.removeEventListener('resize', this._resizeEvent);
      window.clearInterval(this.#resizeTimeout);
      this.#resizeTimeout = false;
    }

  }

  viewportIsWideEnough (windowWidth) {
    return windowWidth > 768;
  }

  onScroll () {
    this.#hasScrolled = true;
  }

  onResize () {
    this.#windowHasResized = true;
  }

  checkScroll () {
    if (this.#hasScrolled === true) {
      this.#hasScrolled = false;
      this.setElementPositions();
    }
  }

  checkResize () {
    const windowWidth = Sticky.getWindowDimensions().width;

    if (this.#windowHasResized === true) {
      this.#windowHasResized = false;

      this._els.forEach(el => {
        if (!this.viewportIsWideEnough(windowWidth)) {
          this.reset(el);
        } else {
          this.setElementDimensions(el);
        }
      });

      if (this.viewportIsWideEnough(windowWidth)) {
        if (_mode === 'dialog') {
          dialog.fitToHeight(this);
          if (dialog.hasResized) {
            dialog.adjustForResize(this);
          }
        }
        this.setElementPositions();
      }
    }
  }

  release (el) {
    if (el.isStuck()) {
      const $el = el.$fixedEl;

      el.removeStickyClasses(this);
      $el.style.width = '';
      // clear styles from any elements stuck while in a dialog mode
      dialog.releaseEl(el, this);
      el.removeShim();
      el.release(this);
    }
  }

  static getWindowDimensions () {
    return {
      height: window.innerHeight,
      width: window.innerWidth
    };
  }

  static getWindowPositions () {
    return {
      scrollTop: window.pageYOffset
    };
  }

}

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
stickAtTop.getInPageEdgePosition = function ($el) {
  return $el.offset().top;
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
    el.stick(this);
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
  var offset = 0;

  if (_mode === 'dialog') {
    offset = dialog.getOffsetFromEdge(el, this);
  }

  el.$fixedEl.css({
    'position': '',
    'top': offset + 'px'
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
stickAtBottom.getInPageEdgePosition = function ($el) {
  return $el.offset().top + $el.outerHeight();
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
    el.stick(this);
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

export {
  stickAtTop as stickAtTopWhenScrolling,
  stickAtBottom as stickAtBottomWhenScrolling
};
