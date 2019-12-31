// Polyfills for any parts of the DOM API available in browsers but not JSDOM

// From: https://gist.github.com/eligrey/1276030
HTMLElement.prototype.insertAdjacentHTML = function(position, html) {
  "use strict";

  var
      ref = this
    , container = ref.ownerDocument.createElementNS("http://www.w3.org/1999/xhtml", "_")
    , ref_parent = ref.parentNode
    , node, first_child, next_sibling
  ;

  container.innerHTML = html;

  switch (position.toLowerCase()) {
    case "beforebegin":
      while ((node = container.firstChild)) {
        ref_parent.insertBefore(node, ref);
      }
      break;
    case "afterbegin":
      first_child = ref.firstChild;
      while ((node = container.lastChild)) {
        first_child = ref.insertBefore(node, first_child);
      }
      break;
    case "beforeend":
      while ((node = container.firstChild)) {
        ref.appendChild(node);
      }
      break;
    case "afterend":
      next_sibling = ref.nextSibling;
      while ((node = container.lastChild)) {
        next_sibling = ref_parent.insertBefore(node, next_sibling);
      }
      break;
  }

};

// from: https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentText#Polyfill
if (!Element.prototype.insertAdjacentText) {
  Element.prototype.insertAdjacentText = function(type, txt){
    this.insertAdjacentHTML(
      type,
      (txt+'') // convert to string
        .replace(/&/g, '&amp;') // embed ampersand symbols
        .replace(/</g, '&lt;') // embed less-than symbols
    )
  }
}
