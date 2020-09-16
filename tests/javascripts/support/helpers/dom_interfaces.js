// helpers for mocking DOM interfaces
// see https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model#DOM_interfaces

// Base class for mocking an DOM APi interfaces not in JSDOM
class DOMInterfaceMock {

  constructor (jest, spec) {

    // set up methods so their calls can be tracked
    // leave implementation/return values to the test
    spec.methods.forEach(method => this[method] = jest.fn(() => {}));

    // set up props
    // any spies should be relative to the test so not set here
    spec.props.forEach(prop => {

      Object.defineProperty(this, prop, {
        get: () => this[prop],
        set: value => this[prop] = value
      });

    });

  }

}

// Very basic class for stubbing the Range interface
// Only contains methods required for current tests
class RangeMock extends DOMInterfaceMock {

  constructor (jest) {
    super(jest, { props: [], methods: ['selectNodeContents', 'setStart'] });
  }

}

// Very basic class for stubbing the Selection interface
// Only contains methods required for current tests
class SelectionMock extends DOMInterfaceMock {

  constructor (jest) {
    super(jest, { props: [], methods: ['removeAllRanges', 'addRange'] });
  }

}

exports.RangeMock = RangeMock;
exports.SelectionMock = SelectionMock;
