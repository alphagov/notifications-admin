// helper to simulate events fired by interactions
// adds positional data for 'click' events to match behaviour of browsers

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

// helpers for simulating events fired by certain interactions
// simulates those fired in Chrome, other browsers vary the events fired

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

}

exports.triggerEvent = triggerEvent;
exports.clickElementWithMouse = clickElementWithMouse;
exports.moveSelectionToRadio = moveSelectionToRadio;
exports.activateRadioWithSpace = activateRadioWithSpace;
