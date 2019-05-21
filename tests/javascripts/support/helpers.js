const triggerEvent = (el, evtType) => {
  const evt = new Event(evtType, {
    bubbles: true,
    cancelable: true
  });

  el.dispatchEvent(evt);
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
exports.element = element;
exports.WindowMock = WindowMock;
