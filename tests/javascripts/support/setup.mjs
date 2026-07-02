// jsdom does not implement the Encoding API (TextEncoder)
// so we need to import it from node utils
import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
