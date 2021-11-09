const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/autofocus.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Autofocus', () => {

  const labelText = 'Search by name';
  let focusHandler;
  let search;

  beforeEach(() => {

    document.title = 'Find services by name - GOV.UK Notify';

    // set up DOM
    document.body.innerHTML =
      `<div id="wrapper">
        <label class="form-label" for="search">
          ${labelText}
        </label>
        <input autocomplete="off" class="form-control form-control-1-1" id="search" name="search" type="search" value="" data-module="autofocus">
      </div>`;

    focusHandler = jest.fn();
    search = document.getElementById('search');
    search.addEventListener('focus', focusHandler, false);

  });

  afterEach(() => {

    document.body.innerHTML = '';
    search.removeEventListener('focus', focusHandler);
    focusHandler = null;

  });

  test('is focused when modules start', () => {

    // start module
    window.GOVUK.modules.start();

    expect(focusHandler).toHaveBeenCalled();

  });

  test('is focused when attribute is set on outer element', () => {

    document.getElementById('search').removeAttribute('data-module');
    document.getElementById('wrapper').setAttribute('data-module', 'autofocus');

    // start module
    window.GOVUK.modules.start();

    expect(focusHandler).toHaveBeenCalled();

  });

  test('is not focused if the window has scrolled', () => {

    // mock the window being scrolled 25px
    $.prototype.scrollTop = jest.fn(() => 25);

    // start module
    window.GOVUK.modules.start();

    expect(focusHandler).not.toHaveBeenCalled();

  });

  test('is focused if the window has scrolled but the force-focus flag is set', () => {

    // mock the window being scrolled 25px
    $.prototype.scrollTop = jest.fn(() => 25);

    // set the force-focus flag
    document.querySelector('#search').setAttribute('data-force-focus', true);

    // start module
    window.GOVUK.modules.start();

    expect(focusHandler).toHaveBeenCalled();

  });

});
