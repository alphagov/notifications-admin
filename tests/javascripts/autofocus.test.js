beforeAll(() => {
  require('../../app/assets/javascripts/autofocus.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Autofocus', () => {

  let focusHandler;
  let search;

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML =
      `<div data-module="autofocus">
        <label class="form-label" for="search">
          Search by name
        </label>
        <input autocomplete="off" class="form-control form-control-1-1" id="search" name="search" type="search" value="">
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
    document.querySelector('div').setAttribute('data-force-focus', true);

    // start module
    window.GOVUK.modules.start();

    expect(focusHandler).toHaveBeenCalled();

  });

});
