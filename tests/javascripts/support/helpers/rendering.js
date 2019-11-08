// helpers for mocking the getting and setting of: position, dimension and scroll position for:
// - elements on the page
// - the page
// - the window

const triggerEvent = require('./events.js').triggerEvent;

function getDescriptorForProperty (prop, obj) {
  const descriptors = Object.getOwnPropertyDescriptors(obj);
  const prototype = Object.getPrototypeOf(obj);

  if ((descriptors !== {}) && (prop in descriptors)) {
    return descriptors[prop];
  }

  // if not in this object's descriptors, check the prototype chain
  if (prototype !== null) {
    return getDescriptorForProperty(prop, prototype);
  }

  // no descriptor for this prop and no prototypes left in the chain
  return null;
};

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

class ScreenRenderItem {
  constructor (jest, node) {

    this._jest = jest;
    this._node = node;
    this._storeProps();
    this._mockAPICalls();

  }

  setData (itemData) {

    // check all the item data is present
    const itemProps = Object.keys(itemData);
    const missingKeys = ScreenRenderItem.REQUIRED_PROPS.filter(prop => !itemProps.includes(prop));

    this._data = {};

    if (missingKeys.length) {
      throw Error(`${itemData.name ? itemData.name : itemProps.join(', ')} is missing these properties: ${missingKeys.join(', ')}`);
    }

    // default left if not set
    if (!('offsetLeft' in itemData)) { itemData.offsetLeft = 0; }

    // copy onto internal store
    Object.assign(this._data, itemData);

  }

  _getBoundingClientRect () {
    const {offsetHeight, offsetWidth, offsetTop, offsetLeft} = this._data;
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

  reset () {

    // reset DOMRect mock
    this._node.getBoundingClientRect.mockClear();

    ScreenRenderItem.OFFSET_PROPS.forEach(prop => {

      if (prop in this._propStore) {
        // replace property implementation
        Object.defineProperty(this._node, prop, this._propStore[prop]);
      }

    });

  }

  _storeProps () {

    this._propStore = {};

    ScreenRenderItem.OFFSET_PROPS.forEach(prop => {
      const descriptor = getDescriptorForProperty(prop, this._node);

      if (descriptor !== null) {
        this._propStore[prop] = descriptor;
      }
    });

  }

  // mock any calls to the node's DOM API for position/dimension
  _mockAPICalls () {

    // proxy getBoundingClientRect and getClientRects calls to item data
    // assumes getClientRects only returns one clientRect
    this._jest.spyOn(this._node, 'getBoundingClientRect').mockImplementation(() => this._getBoundingClientRect());
    this._jest.spyOn(this._node, 'getClientRects').mockImplementation(() => [this._getBoundingClientRect()]);

    // handle calls to offset properties
    ScreenRenderItem.OFFSET_PROPS.forEach(prop => {

      this._jest.spyOn(this._node, prop, 'get').mockImplementation(() => this._data[prop]);

      // proxy DOM API sets for offsetValues (not possible to mock directly)
      Object.defineProperty(this._node, prop, {
        configurable: true,
        set: jest.fn(value => {
          this._data[prop] = value;
          return true;
        })
      });

    });

  }

}
ScreenRenderItem.OFFSET_PROPS = ['offsetHeight', 'offsetWidth', 'offsetTop', 'offsetLeft'];
ScreenRenderItem.REQUIRED_PROPS = ['name', 'offsetHeight', 'offsetHeight', 'offsetWidth', 'offsetTop'];

class ScreenMock {
  constructor (jest) {

    this._jest = jest
    this._items = {};

  }

  mockPositionAndDimension (itemName, node, itemData) {

    if (itemName in this._items) { throw new Error(`${itemName} already has its position and dimension mocked`); }

    const data = Object.assign({ 'name': itemName }, itemData);
    const item = new ScreenRenderItem(this._jest, node);

    item.setData(data);

    this._items[itemName] = item;

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

    Object.keys(this._items).forEach(itemName => this._items[itemName].reset());

  }

}
ScreenMock.REQUIRED_WINDOW_PROPS = ['height', 'width', 'scrollTop'];

exports.WindowMock = WindowMock;
exports.ScreenMock = ScreenMock;
