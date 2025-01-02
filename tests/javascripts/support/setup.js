// Polyfill holes in JSDOM
require('./polyfills.js');

// set up jQuery
window.jQuery = require('jquery');
$ = window.jQuery;

// load module code
require('../../../app/assets/javascripts/modules.js');

const { TextDecoder, TextEncoder } = require('node:util');

// used by cbor2 and jsdom doesn't know about it
Object.defineProperties(globalThis, {
  TextDecoder: { value: TextDecoder, writable: true },
  TextEncoder: { value: TextEncoder, writable: true },
});
