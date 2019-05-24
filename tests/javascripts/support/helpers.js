const triggerEvent = (el, evtType, options) => {
  const eventInit = {
    bubbles: true,
    cancelable: true
  };
  let setPositionData = () => {
    const browserUI = {
      leftFrameBorder: 0,
      topHeight: 100
    };
    const cursorOffset = {
      x: 5,
      y: 5
    };
    const elBoundingBox = el.getBoundingClientRect();

    if (!eventInit.clientX) { eventInit.clientX = elBoundingBox.left + cursorOffset.x; }
    if (!eventInit.clientY) { eventInit.clientY = elBoundingBox.top + cursorOffset.y; }
    if (!eventInit.pageX) { eventInit.pageX = elBoundingBox.left + cursorOffset.x; }
    if (!eventInit.pageY) { eventInit.pageY = elBoundingBox.top + cursorOffset.y; }
    if (!eventInit.screenX) { eventInit.screenX = eventInit.clientX + browserUI.leftFrameBorder; }
    if (!eventInit.screenY) { eventInit.screenY = eventInit.clientY + browserUI.topHeight; }
    if (!eventInit.offsetX) { eventInit.offsetX = cursorOffset.x; }
    if (!eventInit.offsetY) { eventInit.offsetY = cursorOffset.y; }
  };
  let Instance;

  // mixin any specified event properties with the defaults
  if (options && ('eventInit' in options)) {
    Object.assign(eventInit, options.eventInit);
  }

  // use event interface if specified
  if (options && ('interface' in options)) {
    Instance = options.interface;
  } else {

    // otherwise, derive from the event type
    switch (evtType) {
      case 'click':
        // click events are part of the MouseEvent interface
        Instance = window.MouseEvent;
        break;
      case 'mousedown':
        Instance = window.MouseEvent;
        break;
      case 'mouseup':
        Instance = window.MouseEvent;
        break;
      case 'keydown':
        Instance = window.KeyboardEvent;
        break;
      case 'keyup':
        Instance = window.KeyboardEvent;
        break;
      default:
        Instance = Event;
    }

  }

  if (evtType === 'click') {
    // hack for click events to simulate details of pointer interaction
    setPositionData();
  }

  const evt = new Instance(evtType, eventInit);

  el.dispatchEvent(evt);
};

function clickElementWithMouse (el) {
  triggerEvent(el, 'mousedown');
  triggerEvent(el, 'mouseup');
  triggerEvent(el, 'click');
};

function moveSelectionToRadio (el, options) {
  // movement within a radio group with arrow keys fires no keyboard events

  // click event fired from option radio being activated
  triggerEvent(el, 'click', {
    eventInit: { pageX: 0 }
  });

};

function activateRadioWithSpace (el) {

  // simulate events for space key press to confirm selection
  // event for space key press
  triggerEvent(el, 'keydown', {
    eventInit: { which: 32 }
  });
  // click event fired from option radio being activated
  triggerEvent(el, 'click', {
    eventInit: { pageX: 0 }
  });

};

class ElementQuery {
  constructor (el) {
    this.el = el;
  }
  
  get nodeName () {
    return this.el.nodeName.toLowerCase();
  }

  get firstTextNodeValue () {
    const textNodes = Array.from(this.el.childNodes).filter(el => el.nodeType === 3);

    return textNodes.length ? textNodes[0].nodeValue : undefined;
  };
  // returns the elements attributes as an object
  hasAttributesSetTo (mappings) {
    if (!this.el.hasAttributes()) { return false; }

    const keys = Object.keys(mappings);
    let matches = 0;

    keys.forEach(key => {
      if (this.el.hasAttribute(key) && (this.el.attributes[key].value === mappings[key])) {
        matches++;
      }
    });

    return matches === keys.length;
  }

  hasClass (classToken) {
    return Array.from(this.el.classList).includes(classToken);
  }

  is (state) {
    const test = `_is${state.charAt(0).toUpperCase()}${state.slice(1)}`;

    if (ElementQuery.prototype.hasOwnProperty(test)) {
      return this[test]();
    }
  }

  // looks for a sibling before the el that matches the supplied test function
  // the test function gets sent each sibling, wrapped in an Element instance
  getPreviousSibling (test) {
    let node = this.el.previousElementSibling;
    let el;

    while(node) {
      el = element(node);

      if (test(el)) {
        return node;
      }

      node = node.previousElementSibling;
    }

    return null;
  }

  _isHidden () {
    const display = window.getComputedStyle(this.el).getPropertyValue('display');

    return display === 'none';
  }
};

class WindowMock {
  constructor (jest) {
    this._defaults = {
      height: window.innerHeight,
      width: window.innerWidth
    };
    this._spies = {
      document: {}
    };
    this._jest = jest;
  }

  setHeightTo (height) {

    // mock DOM calls for window height
    window.innerHeight = height;
    // remove calls to document.documentElement.clientHeight  when jQuery is gone. It's called to support older browsers like IE8
    this._spies.document.clientHeight = this._jest.spyOn(document.documentElement, 'clientHeight', 'get').mockImplementation(() => height);

  }

  setWidthTo (width) {

    // mock DOM calls for window width
    window.innerWidth = width;
    // remove calls to document.documentElement.clientWidth  when jQuery is gone. It's called to support older browsers like IE8
    this._spies.document.clientWidth = this._jest.spyOn(document.documentElement, 'clientWidth', 'get').mockImplementation(() => height);

  }

  resizeTo (dimensions) {

    this.setHeightTo(dimensions.height);
    this.setWidthTo(dimensions.width);
    triggerEvent(window, 'resize');

  }

  scrollBy (scrollPosition) {

    document.documentElement.scrollTop = scrollPosition;
    triggerEvent(window, 'scroll');

  }

  reset () {

    window.innerHeight = this._defaults.height;
    window.innerWidth = this._defaults.width;
    document.documentElement.scrollTop = 0;

    // reset all spies
    Object.keys(this._spies).forEach(key => {
      const objectSpies = this._spies[key];
      Object.keys(objectSpies).forEach(key => objectSpies[key].mockClear());
    });

  }
}

// function to ask certain questions of a DOM Element
const element = function (el) {
  return new ElementQuery(el);
};

exports.triggerEvent = triggerEvent;
exports.clickElementWithMouse = clickElementWithMouse;
exports.moveSelectionToRadio = moveSelectionToRadio;
exports.activateRadioWithSpace = activateRadioWithSpace;
exports.element = element;
exports.WindowMock = WindowMock;
