class MockAttribute {

    constructor(jest, el, attr) {
        this._jest = jest;
        this._el = el;
        this._attr = attr;
        this.spies = {};
        this._mockAPI();
    }

    _mockAPI() {

        // track calls to get/setAttribute
        this.spies.getAttribute = this._jest.spyOn(this._el, 'getAttribute');
        this.spies.setAttribute = this._jest.spyOn(this._el, 'setAttribute');

        // proxy calls to legacy getters/setters
        this.spies.get = this._jest.spyOn(this._el, this._attr, 'get').mockImplementation(() => this._el.getAttribute(this._attr));
        this.spies.set = this._jest.spyOn(this._el, this._attr, 'set').mockImplementation(value => this._el.setAttribute(this._attr, value));

    }

    reset() {

        Object.keys(this.spies).forEach(key => this.spies[key].mockClear());

    }

}

exports.MockAttribute = MockAttribute;
