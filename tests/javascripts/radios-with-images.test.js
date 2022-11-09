afterAll(() => {
  require('./support/teardown.js');

});

describe('Radios with images', () => {

  let form;
  let radios;

  beforeEach(() => {
    // set up DOM
    document.body.innerHTML =
      `
      <form method="post" autocomplete="off" novalidate="">
        <div class="govuk-form-group">
          <fieldset class="govuk-fieldset" id="banner">
            <legend class="govuk-fieldset__legend govuk-fieldset__legend--l">
              <h1 class="govuk-fieldset__heading">
                Add a banner to your logo
              </h1>
            </legend>
            <div class="govuk-radios notify-radios-with-images govuk-radios--inline">
              <div class="govuk-radios__item notify-radios-with-images__item">
                <img src="/static/images/branding/org.png?4da479dbe00edb51dfac2f38fed58ea2"
                     alt="An example of an email with the heading &quot;Your logo&quot; in blue text on a white background."
                     width="404" height="454" id="banner-0-description" class="notify-radios-with-images__image"
                     data-notify-module="radios-with-images">
                <div class="notify-radios-with-images__radio">
                  <input class="govuk-radios__input" id="banner-0" name="banner" type="radio" value="org"
                         aria-describedby="banner-0-description">
                  <label class="govuk-label govuk-radios__label" for="banner-0">
                    No banner
                  </label>
                </div>
              </div>
              <div class="govuk-radios__item notify-radios-with-images__item">
                <img src="/static/images/branding/org_banner.png?cb13c90781ffbe6f4f3d8e6fab1d2b8b"
                     alt="An example of an email with the heading &quot;Your logo&quot; in white text on a blue banner background."
                     width="404" height="454" id="banner-1-description" class="notify-radios-with-images__image"
                     data-notify-module="radios-with-images">
                <div class="notify-radios-with-images__radio">
                  <input class="govuk-radios__input" id="banner-1" name="banner" type="radio" value="org_banner"
                         aria-describedby="banner-1-description">
                  <label class="govuk-label govuk-radios__label" for="banner-1">
                    Coloured banner
                  </label>
                </div>
              </div>
            </div>
          </fieldset>
        </div>
      </form>

      `;

    form = document.querySelector('form');
    radios = form.querySelector('fieldset');

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // we run the radios-with-images.js script every test
    // the module cache needs resetting each time for the script to execute
    jest.resetModules();
  });

  test('Clicking a image image should select the related radio input', () => {
    // run radios-with-images script
    require('../../app/assets/javascripts/radios-with-images.js');

    // start the module
    window.GOVUK.notifyModules.start();

    expect(document.querySelector('#banner-0').checked).toBe(false);
    expect(document.querySelector('#banner-1').checked).toBe(false);

    document.querySelector('#banner-0-description').click();
    expect(document.querySelector('#banner-0').checked).toBe(true);
    expect(document.querySelector('#banner-1').checked).toBe(false);

    document.querySelector('#banner-1-description').click();
    expect(document.querySelector('#banner-0').checked).toBe(false);
    expect(document.querySelector('#banner-1').checked).toBe(true);
  });

  test('Images should get pointer cursors', () => {
    expect(document.querySelector('#banner-0-description').style.cursor).toBe('');
    expect(document.querySelector('#banner-1-description').style.cursor).toBe('');

    // run radios-with-images script
    require('../../app/assets/javascripts/radios-with-images.js');

    // start the module
    window.GOVUK.notifyModules.start();

    expect(document.querySelector('#banner-0-description').style.cursor).toBe('pointer');
    expect(document.querySelector('#banner-1-description').style.cursor).toBe('pointer');
  });
});
