// helpers for mocking the getting and setting of: position, dimension and scroll position for:
// - elements on the page
// - the page
// - the window

const triggerEvent = require('./events.js').triggerEvent;

class WindowMock {
  constructor (jest) {
    this._defaults = {
      height: window.innerHeight,
      width: window.innerWidth
    };
    this.spies = {
      document: {},
      window: {}
    };
    this._jest = jest;
    this._setSpies();
    this._plugJSDOM();
  }

  get top () {
    return window.scrollY;
  }

  get bottom () {
    return window.scrollY + window.innerHeight;
  }

  get height () {
    return window.innerHeight;
  }

  get width () {
    return window.innerWidth
  }

  get scrollPosition () {
    return window.scrollY;
  }

  _setSpies () {

    // remove calls to document.documentElement.clientHeight when jQuery is gone. It's called to support older browsers like IE8
    this.spies.document.clientHeight = this._jest.spyOn(document.documentElement, 'clientHeight', 'get').mockImplementation(() => window.innerHeight);

    // remove calls to document.documentElement.clientWidth when jQuery is gone. It's called to support older browsers like IE8
    this.spies.document.clientWidth = this._jest.spyOn(document.documentElement, 'clientWidth', 'get').mockImplementation(() => window.innerWidth);

  }

  _plugJSDOM () {

    const self = this;

    // JSDOM doesn't support .scrollTo
    this.spies.window.scrollTo = this._jest.fn(function () {
      let y;

      // data sent as props in an object
      if (arguments.length === 1) {
        y = arguments[0].y;
      } else {
        y = arguments[1];
      }

      self.scrollTo(y);

    });

     window.scrollTo = this.spies.window.scrollTo;

  }

  setHeightTo (height) {

    window.innerHeight = height;

  }

  setWidthTo (width) {

    window.innerWidth = width;

  }

  resizeTo (dimensions) {

    this.setHeightTo(dimensions.height);
    this.setWidthTo(dimensions.width);
    triggerEvent(window, 'resize');

  }

  scrollTo (scrollPosition) {

    document.documentElement.scrollTop = scrollPosition;
    window.scrollY = scrollPosition;
    window.pageYOffset = scrollPosition;

    triggerEvent(window, 'scroll');

  }

  reset () {

    window.innerHeight = this._defaults.height;
    window.innerWidth = this._defaults.width;
    this.scrollTo(0);

    // reset all spies
    Object.keys(this.spies).forEach(key => {
      const objectSpies = this.spies[key];
      Object.keys(objectSpies).forEach(key => objectSpies[key].mockClear());
    });

  }
}

class MockedElementItem {
  constructor (jest, itemName, nodeRef) {

    this._jest = jest;
    this.itemName = itemName;
    this.nodeRef = nodeRef;
    this.data = {};

    // The mocked methods will run on an element, so `this` will reference it
    // Use a closure to give them access to this.data
    this.getBoundingClientRect = this.mockGetBoundingClientRect(this.data);
    this.getClientRects = this.mockGetClientRects(this.data);

  }

  setData (itemData) {

    // check all the item data is present
    const itemProps = Object.keys(itemData);
    const missingKeys = MockedElementItem.REQUIRED_PROPS.filter(prop => !itemProps.includes(prop));

    if (missingKeys.length) {
      throw Error(`${this.itemName} is missing these properties: ${missingKeys.join(', ')}`);
    }

    // default left if not set
    if (!('offsetLeft' in itemData)) { itemData.offsetLeft = 0; }

    // copy onto internal store
    Object.assign(this.data, itemData);

  }

  mockGetBoundingClientRect (data) {

    return function () {

      const {offsetHeight, offsetWidth, offsetTop, offsetLeft} = data;
      const x = offsetLeft - window.scrollX;
      const y = offsetTop - window.scrollY;

      return {
        'x': x,
        'y': y,
        'top': (offsetHeight < 0) ? y + offsetHeight : y,
        'left': (offsetWidth < 0) ? x + offsetWidth : x,
        'bottom': (offsetTop + offsetHeight) - window.scrollY,
        'right': (offsetLeft + offsetWidth) - window.scrollX,
      };

    }

  }

  mockGetClientRects (data) {

    return function () {

      return [this.getBoundingClientRect()]

    }

  }

}

MockedElementItem.OFFSET_PROPS = ['offsetHeight', 'offsetWidth', 'offsetTop', 'offsetLeft'];
MockedElementItem.REQUIRED_PROPS = ['offsetHeight', 'offsetWidth', 'offsetTop'];

class ScreenMock {
  constructor (jest) {

    this._jest = jest
    this._mockedElements = {};
    this._descriptorStore = {};
    this._patchClientRectsMethods();
    this._patchOffsetProps();

  }

  // nodeRef can be either of:
  // - an element node
  // - a CSS selector string matching an element
  //
  // So check which type and if it matches the sent node
  _matchesNode (node, nodeRef) {

    if (nodeRef instanceof Element) {
      return node === nodeRef;
    }

    // nodeRef not pointing to an actual Node are assumed to be CSS selector strings
    return node === document.querySelector(nodeRef);

  }

  _getMockItemForElement (el) {

    const matches = Object.values(this._mockedElements).filter(
      mockedElementItem => this._matchesNode(el, mockedElementItem.nodeRef)
    );

    if (matches.length === 0) {
      return null;
    }

    return matches[0];

  }


  // Add getClientRects & getBoundingClientRect for all HTML elements.
  // HTMLElement normally delegates to Element.prototype for those methods.
  // This replaces them at the HTMLElement level with custom logic that either
  // - uses a mocked version on the mockedElementItem for the element, if it exists, or
  // - delegates to the original method on Element.prototype if not
  _patchClientRectsMethods () {

    const _self = this;

    // Replace with function that uses mockedElement if exists or falls back to variant of original
    HTMLElement.prototype.getBoundingClientRect = function () {
      const mockedElementItem = _self._getMockItemForElement(this);

      if (mockedElementItem === null) {
        return Element.prototype.getBoundingClientRect.bind(this)()
      } else {
        return mockedElementItem.getBoundingClientRect.bind(this)()
      }
    };

    HTMLElement.prototype.getClientRects = function () {
      const mockedElementItem = _self._getMockItemForElement(this);

      if (mockedElementItem === null) {
        return Element.prototype.getClientRects.bind(this)()
      } else {
        return mockedElementItem.getClientRects.bind(this)()
      }
    };

  }

  // Patch offset props by replacing them with property descriptors that either
  // - access the mocked data, if a mockedElementItem exists for the element, or
  // - pass through to the getter/setter on the original descriptor if not
  _patchOffsetProps () {

    MockedElementItem.OFFSET_PROPS.forEach(prop => {

      const _self = this;
      const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop);

      // Cache the original descriptor, for reinstatement later
      this._descriptorStore[prop] = descriptor;

      // Replace property with custom that returns mocked data
      Object.defineProperty(HTMLElement.prototype, prop, {
        configurable: true,
        get: function () {

          const mockItemForElement = _self._getMockItemForElement(this);

          // Return mocked data, if present
          if (mockItemForElement !== null) {
            return mockItemForElement.data[prop];
          }

          // Otherwise, use the original descriptor
          return descriptor.get.bind(this)();

        },
        set: function (val) {

          const mockItemForElement = _self._getMockItemForElement(this);

          // Set mocked data to value, if present
          if (mockItemForElement !== null) {
            mockItemForElement.data[prop] = val;
          }

          // Otherwise, use the original descriptor
          if (descriptor.set !== undefined) { // offset props are readonly so guard against this
            descriptor.set.bind(this)(val);
          }

        }
      });

    });

  }

  // Clear mock methods getClientRects & getBoundingClientRect method to return element to default state
  _resetHTMLElementMethods () {

    // Go back to HTMLElement having no copy of these methods on its own prototype.
    // It normally herits them from Element, it's parent class.
    // Deleting them here will go back to that state.
    delete HTMLElement.prototype.getClientRects;
    delete HTMLElement.prototype.getBoundingClientRect;

  }

  // Use original property descriptors to return all offset properties to their default state
  _resetHTMLElementProps () {

    MockedElementItem.OFFSET_PROPS.forEach(prop => {

      if (prop in this._descriptorStore) {
        // Replace property implementation
        Object.defineProperty(HTMLElement.prototype, prop, this._descriptorStore[prop]);
      }

    });

  }

  mockPositionAndDimension (itemName, nodeRef, itemData) {

    if (arguments.length < 3) {
      throw new Error(`ScreenMock.mockPositionAndDimension needs itemName, nodeRef and itemData. ${arguments.join(', ')} provided`);
    }

    if (itemName in this._mockedElements) {
      throw new Error(`An element called '${itemName}' already has its position and dimension mocked`);
    }

    const item = new MockedElementItem(this._jest, itemName, nodeRef);

    item.setData(itemData);

    this._mockedElements[itemName] = item;

  }

  setWindow (windowData) {

    this.window = new WindowMock(this._jest);

    // check all the window data is present
    const missingKeys = Object.keys(windowData).filter(key => !ScreenMock.REQUIRED_WINDOW_PROPS.includes(key));

    if (missingKeys.length) {
      throw Error(`Window definition is missing these properties: ${missingKeys.join(', ')}`);
    }

    this.window.setHeightTo(windowData.height);
    this.window.setWidthTo(windowData.width);
    this.window.scrollTo(windowData.scrollTop);

  }

  scrollTo (scrollTop) {

    this.window.scrollTo(scrollTop);

  }

  reset () {

    this._resetHTMLElementProps();
    this._resetHTMLElementMethods();

  }

}
ScreenMock.REQUIRED_WINDOW_PROPS = ['height', 'width', 'scrollTop'];

exports.WindowMock = WindowMock;
exports.ScreenMock = ScreenMock;
