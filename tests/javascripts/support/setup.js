// Polyfill holes in JSDOM
require('./polyfills.js');

// jsdom does not implement the Encoding API (TextEncoder)
// so we need to import it from node utils
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// set up jQuery
window.jQuery = require('jquery');
$ = window.jQuery;

// load module code
require('../../../app/assets/javascripts/modules.js');
