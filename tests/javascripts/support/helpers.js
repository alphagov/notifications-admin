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

function getRadios (fields) {
  const result = '';

  return fields.map((field, idx) => {
    const count = idx + 1;

    return `
      <div class="multiple-choice">
        <input id="choose-${field.name}-1" name="choose-${field.name}-1" type="radio" value="${field.value}" ${field.checked ? 'checked' : ''}>
        <label class="block-label" for="choose-${field.name}-1">
          ${field.label}
        </label>
      </div>`;
  }).join("\n");
};

function getRadioGroup (data) {
  let radioGroup = document.createElement('div');

  data.cssClasses.forEach(cssClass => radioGroup.classList.add(cssClass));
  radioGroup.innerHTML = `
    <div class="form-group ">
      <fieldset id="choose-${data.name}">
        <legend class="form-label">
           Choose ${data.label}
        </legend>
        ${getRadios(data.fields)}
      </fieldset>
    </div>`;

    return radioGroup;
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

// Base class for mocking an DOM APi interfaces not in JSDOM
class DOMInterfaceMock {

  constructor (jest, spec) {

    // set up methods so their calls can be tracked
    // leave implementation/return values to the test
    spec.methods.forEach(method => this[method] = jest.fn(() => {}));

    // set up props
    // any spies should be relative to the test so not set here
    spec.props.forEach(prop => {

      Object.defineProperty(this, prop, {
        get: () => this[prop],
        set: value => this[prop] = value
      });

    });

  }

}

// Very basic class for stubbing the Range interface
// Only contains methods required for current tests
class RangeMock extends DOMInterfaceMock {

  constructor (jest) {
    super(jest, { props: [], methods: ['selectNodeContents'] });
  }

}

// Very basic class for stubbing the Selection interface
// Only contains methods required for current tests
class SelectionMock extends DOMInterfaceMock {

  constructor (jest) {
    super(jest, { props: [], methods: ['removeAllRanges', 'addRange'] });
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

    // proxy boundingClientRect property calls to item data
    this._jest.spyOn(this._node, 'getBoundingClientRect').mockImplementation(() => this._getBoundingClientRect());

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

// function to ask certain questions of a DOM Element
const element = function (el) {
  return new ElementQuery(el);
};

exports.triggerEvent = triggerEvent;
exports.clickElementWithMouse = clickElementWithMouse;
exports.moveSelectionToRadio = moveSelectionToRadio;
exports.activateRadioWithSpace = activateRadioWithSpace;
exports.RangeMock = RangeMock;
exports.SelectionMock = SelectionMock;
exports.getRadioGroup = getRadioGroup;
exports.getRadios = getRadios;
exports.element = element;
exports.WindowMock = WindowMock;
exports.ScreenMock = ScreenMock;
