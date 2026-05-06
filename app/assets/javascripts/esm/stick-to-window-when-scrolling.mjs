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
    this.els = [el];
    this.edge = edge;
    this.selector = selector;
    this.node = $scrollArea;
    this.setEvents();
  }

  addEl (el) {
    this.els.push(el);
  }

  hasEl (el) {
    return this.els.includes(el);
  }

  updateEls (usedEls) {
    this.els = usedEls;
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
    const endOfFurthestEl = focusOverlap.endOfFurthestEl(this.els, this.edge);
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
    const matches = this.#scrollAreas.filter(area => area.els.includes(el));

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
    const stuckEls = els.filter((el) => el.isStuck);
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
      els = sticky.els;
    }

    els = els.filter((el) => el.isStuck);

    els.forEach((el) => el.$fixedEl.classList.add(edgeClass));
  }

  unmark (sticky) {
    const edgeClass = this.#classes[sticky.edge];

    sticky.els.forEach(el => el.$fixedEl.classList.remove(edgeClass));
  }

}
const oppositeEdge = new OppositeEdge();


// Constructor for objects holding data for each element to have sticky behaviour
class StickyElement {
  #initialFixedClass = 'content-fixed-onload';
  #fixedClass = 'content-fixed';
  #appliedClass = null;
  #stopped = false;
  #hasLoaded = false;
  #canBeStuck = true;
  #sticky;

  constructor ($el, sticky) {
    this.#sticky = sticky;
    this.$fixedEl = $el;
    this.$shim = null;

    const marginTop = window.getComputedStyle(this.$fixedEl)['margin-top'];
    const marginBottom = window.getComputedStyle(this.$fixedEl)['margin-bottom'];

    this.verticalMargins = {
      'top': (marginTop !== '') ? parseInt(marginTop, 10) : null,
      'bottom': (marginBottom !== '') ? parseInt(marginBottom, 10) : null
    };
  }

  #getShimCSS () {
    let inlineStyles = `width: ${this.horizontalSpace}px; height: ${this.height}px`;

    if (this.verticalMargins.top) {
      inlineStyles += `; margin-top: ${this.verticalMargins.top}px`;
    }
    if (this.verticalMargins.bottom) {
      inlineStyles += `; margin-bottom: ${this.verticalMargins.bottomtop}px`;
    }
    return inlineStyles;
  }

  stickyClass () {
    return (this.#sticky.initialPositionsSet) ? this.#fixedClass : this.#initialFixedClass;
  }

  appliedClass () {
    return this.#appliedClass;
  }

  removeStickyClasses () {
    this.$fixedEl.classList.remove(this.#initialFixedClass, this.#fixedClass);
  }

  get isStuck () {
    return this.#appliedClass !== null;
  }

  stick () {
    this.#appliedClass = this.stickyClass();
    this.$fixedEl.classList.add(this.#appliedClass);
  }

  release () {
    this.#appliedClass = null;
    this.removeStickyClasses();
  }

  // When a sticky element is moved into the 'stuck' state, a shim is inserted into the
  // page to preserve the space the element occupies in the flow.
  addShim (position) {
    const insertPosition = (position === 'before') ? 'beforebegin' : 'afterend';

    this.$shim = document.createElement('div');
    this.$shim.innerHTML = '&nbsp;'; // we should use createTextNode but it won't take HTML entities
    this.$shim.classList.add('shim');
    this.$shim.setAttribute('style', this.#getShimCSS());
    this.$fixedEl.insertAdjacentElement(insertPosition, this.$shim);
  }

  removeShim () {
    if (this.$shim !== null) {
      this.$shim.remove();
      this.$shim = null;
    }
  }

  // Changes to the dimensions of a sticky element with a shim need to be passed on to the shim
  updateShim () {
    if (this.$shim) {
      this.$shim.setAttribute('style', this.#getShimCSS());
    }
  }

  stop () {
    this.#stopped = true;
  }

  unstop () {
    this.#stopped = false;
  }

  get isStopped () {
    return this.#stopped;
  }

  get isInPage () {
    const node = this.$fixedEl;
    return (node === document.body) ? false : document.body.contains(node);
  }

  get canBeStuck () {
    return this.#canBeStuck;
  }

  set canBeStuck (val) {
    this.#canBeStuck = val;
  }

  get hasLoaded () {
    return this.#hasLoaded;
  }

  set hasLoaded (val) {
    this.#hasLoaded = val;
  }

}

// Class for treating sticky elements as if they were wrapped by a dialog component
class Dialog {
  static spaceBetweenStickys = 40;

  constructor () {
    this.hasResized = false;
  }

  // we add padding of 20px around each sticky to give some space between it and the rest of the page
  // this shouldn't apply between stickys in a stack
  // (the in-page CSS handles this by each subsequent sticky in a sequence having margin: -40px)
  #getPaddingBetweenEls (els) {
    if (els.length <= 1) { return 0; }

    return (els.length - 1) * Dialog.spaceBetweenStickys;
  }

  #getTotalHeight (els) {
    const reducer = (accumulator, currentValue) => {
      return accumulator + currentValue;
    };
    const combinedHeight = els.map(el => el.height).reduce(reducer);

    return combinedHeight - this.#getPaddingBetweenEls(els);
  }

  #elsThatCanBeStuck (els) {
    return els.filter(el => el.canBeStuck);
  }

  getOffsetFromEdge (el, sticky) {
    let els = this.#elsThatCanBeStuck(sticky.els).slice();

    // els must be arranged furtherest from window edge is stuck to first
    // default direction is order in document
    if (sticky.edge === 'top') {
      els.reverse();
    }

    const elIdx = els.indexOf(el);

    // if next to window edge the dialog is stuck to, no offset
    if (elIdx === (els.length - 1)) { return 0; }

    // make els all those from this one to the window edge
    els = els.slice(elIdx + 1);

    // remove the space between those els and the one on the edge
    return this.#getTotalHeight(els) - Dialog.spaceBetweenStickys;
  }

  getOffsetFromEnd (el, sticky) {
    let els = this.#elsThatCanBeStuck(sticky.els);

    // els must be arranged furtherest from window edge is stuck to first
    // default direction is order in document
    if (sticky.edge === 'bottom') {
      els.reverse();
    }

    const elIdx = els.indexOf(el);

    // if next to opposite edge to the one the dialog is stuck to, no offset
    if (elIdx === (els.length - 1)) { return 0; }

    // make els all those from this one to the window edge
    els = els.slice(elIdx + 1);

    return this.#getTotalHeight(els) - Dialog.spaceBetweenStickys;
  }

  // checks total height of all this._sticky elements against a height
  // unsticks each that won't fit and marks them as unstickable
  fitToHeight (sticky) {
    const self = this;
    const els = sticky.els.slice();
    const height = Sticky.getWindowDimensions().height;
    const totalStickyHeight = () => self.#getTotalHeight(self.#elsThatCanBeStuck(els));
    const dialogFitsHeight = () => totalStickyHeight() <= height;

    // els must be arranged furtherest from window edge is stuck to first
    // default direction is order in document
    if (sticky.edge === 'top') {
      els.reverse();
    }

    // reset elements
    els.forEach(el => el.canBeStuck = true);

    while (self.#elsThatCanBeStuck(els).length && !dialogFitsHeight()) {
      const currentEl = self.#elsThatCanBeStuck(els)[0];

      sticky.reset(currentEl);
      currentEl.canBeStuck = false;

      if (!self.hasResized) { self.hasResized = true; }
    }
  }

  getElementAtStickyEdge (sticky) {
    const els = this.#elsThatCanBeStuck(sticky.els);
    const idx = (sticky.edge === 'top') ? 0 : els.length - 1;

    return els[idx];
  }

  // get element at the end opposite the sticky edge
  getElementAtOppositeEnd (sticky) {
    const els = this.#elsThatCanBeStuck(sticky.els);
    const idx = (sticky.edge === 'top') ? els.length - 1 : 0;

    return els[idx];
  }

  getInPageEdgePosition (sticky) {
    return this.getElementAtStickyEdge(sticky).inPageEdgePosition;
  }

  getHeight (els) {
    return this.#getTotalHeight(this.#elsThatCanBeStuck(els));
  }

  adjustForResize (sticky) {
    const windowHeight = Sticky.getWindowDimensions().height;

    if (sticky.edge === 'top') {
      window.scrollTo(window.pageXOffset, this.getInPageEdgePosition(sticky));
    } else {
      window.scrollTo(window.pageXOffset, this.getInPageEdgePosition(sticky) - windowHeight);
    }

    this.hasResized = false;
  }

  releaseEl (el, sticky) {
    el.$fixedEl.style[sticky.edge] = '';
  }

}
const dialog = new Dialog();

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
    this.els = [];
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

    this.els.forEach(el => {
      if (el.canBeStuck) {
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
    if (el.isStopped) {
      this.unstop(el);
    }

    if (el.isStuck) {
      this.release(el);
    }
  }

  // Recalculate stored dimensions for all sticky elements
  recalculate () {
    const onSyncComplete = () => {
      scrollAreas.syncEls(this.els);
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

    if (!el.hasLoaded && ($img !== null)) {
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
    return this.els.length === totalEls;
  }

  getElForNode (node) {
    const matches = this.els.filter(el => el.$fixedEl === node);

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
        this.els.push(elObj);
      }

      if (setPositions) {
        this.setElementPositions();
      }

      if (cb !== undefined) {
        cb();
      }
    };

    if (!exists) {
      elObj = new StickyElement($el, this);
      scrollAreas.addEl(elObj, this.edge, this.CSS_SELECTOR);
    }

    this.setElementDimensions(elObj, onDimensionsSet);
  }

  remove (el) {
    if (this.els.includes(el)) {

      // reset DOM node to original state
      this.reset(el);

      // remove sticky element object
      this.els = this.els.filter(_el => _el !== el);
    }
  }

  // gets all sticky elements in the DOM and removes any in this.els no longer in attached to it
  syncWithDOM (callback) {
    const $els = document.querySelectorAll(this.CSS_SELECTOR);
    const numOfEls = $els.length;

    const onLoaded = () => {
      if (this.els.length === numOfEls) {
        this.endOfScrollArea = this.getEndOfScrollArea();
        if (callback !== undefined) {
          callback();
        }
      }
    };

    // remove any els no longer in the DOM
    if (this.els.length) {
      this.els.forEach(el => {
        if (!el.isInPage) {
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

      this.els.forEach(el => {
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
    if (el.isStuck) {
      const $el = el.$fixedEl;

      el.removeStickyClasses(this);
      $el.style.width = '';
      // clear styles from any elements stuck while in a dialog mode
      dialog.releaseEl(el, this);
      el.removeShim();
      el.release();
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
class StickAtTop extends Sticky {
  constructor () {
    super('.js-stick-at-top-when-scrolling');
    this.edge = 'top';
  }

  // Store furthest point sticky elements are allowed
  getEndOfScrollArea () {
    const footer = document.querySelector('.js-footer');
    if (footer === null) {
      return 0;
    }
    return offset(footer).top - this.STOP_PADDING;
  }

  // position of the bottom edge when in the page flow
  getInPageEdgePosition ($el) {
    return offset($el).top;
  }

  getScrolledFrom (el) {
    if (_mode === 'dialog') {
      return dialog.getInPageEdgePosition(this);
    } else {
      return el.inPageEdgePosition;
    }
  }

  getScrollingTo (el) {
    let height = el.height;

    if (_mode === 'dialog') {
      height = dialog.getHeight(this.els);
    }

    return this.endOfScrollArea - height;
  }

  getStoppingPosition (el) {
    let offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEnd(el, this);
    }

    return (this.endOfScrollArea - offset) - el.height;
  }

  windowNotPastScrolledFrom (windowPositions, scrolledFrom) {
    return scrolledFrom > windowPositions.top;
  }

  windowNotPastScrollingTo (windowPositions, scrollingTo) {
    return windowPositions.top < scrollingTo;
  }

  stick (el) {
    if (!el.isStuck) {
      const $el = el.$fixedEl;
      let offset = 0;

      if (_mode === 'dialog') {
        offset = dialog.getOffsetFromEdge(el, this);
      }

      el.addShim('before');
      $el.style.width = $el.getBoundingClientRect().width + 'px';
      $el.style.top = offset + 'px';
      el.stick();
    }
  }

  stop (el) {
    if (!el.isStopped) {
      el.$fixedEl.style.position = 'absolute';
      el.$fixedEl.style.top = this.getStoppingPosition(el) + 'px';
      el.stop();
    }
  }

  unstop (el) {
    let offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEdge(el, this);
    }

    el.$fixedEl.style.position = '';
    el.$fixedEl.style.top = offset + 'px';
    el.unstop();
  }

}
const stickAtTop = new StickAtTop();

// Extension of sticky object to add behaviours specific to sticking to bottom of window
class StickAtBottom extends Sticky {
  constructor () {
    super('.js-stick-at-bottom-when-scrolling');
    this.edge = 'bottom';
  }

  // Store furthest point sticky elements are allowed
  getEndOfScrollArea () {
    const header = document.querySelector('.js-header');
    if (header === null) {
      return 0;
    }
    return (offset(header).top + header.offsetHeight) + this.STOP_PADDING;
  }

  // position of the bottom edge when in the page flow
  getInPageEdgePosition ($el) {
    return offset($el).top + $el.offsetHeight;
  }

  getScrolledFrom (el) {
    if (_mode === 'dialog') {
      return dialog.getInPageEdgePosition(this);
    } else {
      return el.inPageEdgePosition;
    }
  }

  getScrollingTo (el) {
    let height = el.height;

    if (_mode === 'dialog') {
      height = dialog.getHeight(this.els);
    }

    return this.endOfScrollArea + height;
  }

  getStoppingPosition (el) {
    let offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEnd(el, this);
    }

    return this.endOfScrollArea + offset;
  }

  windowNotPastScrolledFrom (windowPositions, scrolledFrom) {
    return scrolledFrom < windowPositions.bottom;
  }

  windowNotPastScrollingTo (windowPositions, scrollingTo) {
    return windowPositions.bottom > scrollingTo;
  }

  stick (el) {
    if (!el.isStuck) {
      const $el = el.$fixedEl;
      let offset = 0;

      if (_mode === 'dialog') {
        offset = dialog.getOffsetFromEdge(el, this);
      }

      el.addShim('after');
      // element will be absolutely positioned so cannot rely on parent element for width
      $el.style.width = $el.getBoundingClientRect().width + 'px';
      $el.style.bottom = offset + 'px';
      el.stick();
    }
  }

  stop (el) {
    if (!el.isStopped) {
      el.$fixedEl.style.position = 'absolute';
      el.$fixedEl.style.top = this.getStoppingPosition(el) + 'px';
      el.$fixedEl.style.bottom = 'auto';
      el.stop();
    }
  }

  unstop (el) {
    let offset = 0;

    if (_mode === 'dialog') {
      offset = dialog.getOffsetFromEdge(el, this);
    }

    el.$fixedEl.style.position = '';
    el.$fixedEl.style.top = '';
    el.$fixedEl.style.bottom = offset + 'px';
    el.unstop();
  }

}
const stickAtBottom = new StickAtBottom;

export {
  stickAtTop as stickAtTopWhenScrolling,
  stickAtBottom as stickAtBottomWhenScrolling
};
