import Autofocus from '../../app/assets/javascripts/esm/autofocus.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers';

describe('Autofocus', () => {

  const labelText = 'Search by name';
  let focusHandler;
  let search;
  let screenMock;

  beforeEach(() => {
    // add class to mimic IRL 
    document.body.classList.add('govuk-frontend-supported')
    document.title = 'Find services by name - GOV.UK Notify';

    screenMock = new helpers.ScreenMock(jest);
    screenMock.setWindow({
      width: 1200,
      height: 600,
      scrollTop: 0
    });

    // set up DOM
    document.body.innerHTML =
      `<div id="wrapper">
        <label class="form-label" for="search">
          ${labelText}
        </label>
        <input autocomplete="off" class="form-control form-control-1-1" id="search" name="search" type="search" value="" data-notify-module="autofocus">
      </div>`;

    focusHandler = jest.fn();
    search = document.getElementById('search');
    search.addEventListener('focus', focusHandler, false);

  });

  afterEach(() => {

    document.body.innerHTML = '';
    search.removeEventListener('focus', focusHandler);
    focusHandler = null;
    screenMock.reset();

  });

  test('is focused when modules start', () => {

    // start module
    new Autofocus(document.querySelector('[data-notify-module="autofocus"]'))

    expect(focusHandler).toHaveBeenCalled();

  });

  test('is focused when attribute is set on outer element', () => {

    document.getElementById('search').removeAttribute('data-notify-module');
    document.getElementById('wrapper').setAttribute('data-notify-module', 'autofocus');

    // start module
    new Autofocus(document.querySelector('[data-notify-module="autofocus"]'))

    expect(focusHandler).toHaveBeenCalled();

  });

  test('is not focused if the window has scrolled', () => {

    // mock the window being scrolled 25px
    screenMock.scrollTo(25);

    // start module
    new Autofocus(document.querySelector('[data-notify-module="autofocus"]'))

    expect(focusHandler).not.toHaveBeenCalled();

  });

  test('is focused if the window has scrolled but the force-focus flag is set', () => {

    // mock the window being scrolled 25px
    screenMock.scrollTo(25);

    // set the force-focus flag
    document.querySelector('#search').setAttribute('data-force-focus', true);

    // start module
    new Autofocus(document.querySelector('[data-notify-module="autofocus"]'))

    expect(focusHandler).toHaveBeenCalled();

  });

});
