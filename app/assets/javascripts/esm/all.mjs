// JS Module used to combine all the JS modules used in the application into a single entry point,
// a bit like `app/__init__` in the Flask app.
//
// When processed by a bundler, this is turned into a Immediately Invoked Function Expression (IIFE)
// The IIFE format allows it to run in browsers that don't support JS Modules.
//
// Exported items will be added to the window.GOVUK namespace.
// For example, `export { Frontend }` will assign `Frontend` to `window.Frontend`

// GOVUK Frontend modules


// Modules from 3rd party vendors
import morphdom from 'morphdom';

var vendor = {
  "morphdom": morphdom,
}

// The exported object will be assigned to window.GOVUK in our production code
// (bundled into an IIFE by RollupJS)
export {
  vendor
}
