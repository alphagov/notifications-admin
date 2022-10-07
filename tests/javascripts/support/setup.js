// Polyfill holes in JSDOM
require('./polyfills.js');

// set up jQuery
window.jQuery = require('jquery');
$ = window.jQuery;

// load module code
require('../../../app/assets/javascripts/modules.js');
