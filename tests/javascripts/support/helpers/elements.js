// helpers for getting information about DOM nodes

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
}

// function to ask certain questions of a DOM Element
function element (el) {
  return new ElementQuery(el);
}

exports.element = element;
