// helpers for mocking objects attached to the global space as properties, ie. window.location

class LocationMock {

  constructor (URL) {

    this._location = window.location;

    // setting href sets all sub-properties
    this.href = URL;

    // JSDOM sets window.location as non-configurable
    // the only way to mock it, currently, is to replace it completely
    delete window.location;
    window.location = this;

  }

  get href () {

    return `${this.protocol}://${this.host}${this.pathname}${this.search}${this.hash}`

  }

  set href (value) {

    const partNames = ['protocol', 'hostname', 'port', 'pathname', 'search', 'hash'];

    const protocol = '(https:|http:)';
    const hostname = '[^\\/]+';
    const port = '(:\\d)';
    const pathname = '([^?]+)';
    const search = '([^#])';
    const hash = '(#[\\x00-\\x7F])'; // match any ASCII character

    const re = new RegExp(`^${protocol}{0,1}(?:\\/\\/){0,1}(${hostname}${port}{0,1}){0,1}${pathname}{0,1}${search}{0,1}${hash}{0,1}$`);
    const match = value.match(re)

    if (match === null) { throw Error(`${value} is not a valid URL`); }

    match.forEach((part, idx) => {

      let partName;

      // 0 index is whole match, we want the groups
      if (idx > 0) {
        partName = partNames[idx - 1];

        if (part !== undefined) {
          this[partName] = part;
        } else if (!(partName in this)) { // only get value from window.location if property not set
          this[partName] = this._location[partName];
        }
      }

    });

  }

  get host () {

    return `${this.hostname}:${this.port}`;

  }

  set host (value) {

    const parts = value.split(':');

    this.hostname = parts[0];
    this.protocol = parts[1];

  }

  // origin is read-only
  get origin () {

    return `${this.protol}://${this.hostname}`;

  }

  reset () {

    window.location = this._location;

  }
}

exports.LocationMock = LocationMock;
