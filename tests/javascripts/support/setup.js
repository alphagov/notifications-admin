// jsdom does not implement the Encoding API (TextEncoder)
// so we need to import it from node utils
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
