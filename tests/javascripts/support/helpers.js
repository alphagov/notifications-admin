const globals = require('./helpers/globals.js');
const events = require('./helpers/events.js');
const domInterfaces = require('./helpers/dom_interfaces.js');
const cookies = require('./helpers/cookies.js');
const html = require('./helpers/html.js');
const elements = require('./helpers/elements.js');
const rendering = require('./helpers/rendering.js');
const utilities = require('./helpers/utilities.js');

exports.LocationMock = globals.LocationMock;
exports.triggerEvent = events.triggerEvent;
exports.clickElementWithMouse = events.clickElementWithMouse;
exports.moveSelectionToRadio = events.moveSelectionToRadio;
exports.activateRadioWithSpace = events.activateRadioWithSpace;
exports.RangeMock = domInterfaces.RangeMock;
exports.SelectionMock = domInterfaces.SelectionMock;
exports.getCookie = cookies.getCookie;
exports.setCookie = cookies.setCookie;
exports.getRadioGroup = html.getRadioGroup;
exports.getRadios = html.getRadios;
exports.templatesAndFoldersCheckboxes = html.templatesAndFoldersCheckboxes;
exports.element = elements.element;
exports.WindowMock = rendering.WindowMock;
exports.ScreenMock = rendering.ScreenMock;
exports.getFormDataFromPairs = utilities.getFormDataFromPairs;
