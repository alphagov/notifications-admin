// helpers for mocking objects attached to the global space as properties, ie. window.location

class LocationMock {

  constructor () {

    const _url = new window.URL(window.location.href);
    this._location = window.location;

    // proxy use of properties to equivalent from window.URL instance
    ['protocol', 'hostname', 'port', 'pathname', 'search', 'hash', 'href'].forEach(partName => {

      Object.defineProperty(this, partName, {
        get: function () { return _url[partName]; },
        set: function (value) { _url[partName] = value; }
      });

    });

    // JSDOM sets window.location as non-configurable
    // the only way to mock it, currently, is to replace it completely
    delete window.location;
    window.location = this;

  }

  // empty method for mocking
  reload () {

  }

  // empty method for mocking
  assign () {

  }

  // custom method to reset window.location to the original. Not part of the window.location API
  reset () {

    window.location = this._location;

  }
}

exports.LocationMock = LocationMock;
