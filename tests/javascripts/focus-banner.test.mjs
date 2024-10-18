import FocusBanner from '../../app/assets/javascripts/esm/focus-banner.mjs'

describe('Focus banner', () => {

  beforeAll(() => {
    document.body.classList.add('govuk-frontend-supported');
  });

  test('It focuses any div.banner-dangerous elements when the page loads', () => {

    document.body.innerHTML = `
      <div class="banner-dangerous">
        <h2>This is a problem with your upload</h2>
        <p>The file uploaded needs to be a PNG</p>
      </div>`;

    (new FocusBanner());

    const bannerEl = document.querySelector('.banner-dangerous');

    expect(document.activeElement).toBe(bannerEl);

    $(bannerEl).trigger('blur');

    expect(bannerEl.hasAttribute('tabindex')).toBe(false);

  });

  describe('It focuses banner elements when they appear in content updated by AJAX', () => {

    test('If there is a div.banner-dangerous in the updated content, it should be focused', () => {

      document.body.innerHTML = `
        <div class="ajax-block-container">
        </div>`;

      const ajaxBlockContainer = document.querySelector('.ajax-block-container');

      (new FocusBanner());

      // simulate a content update event
      ajaxBlockContainer.innerHTML = `
        <div class="banner-dangerous">
          <h2>This is a problem with your upload</h2>
          <p>The file uploaded needs to be a PNG</p>
        </div>`;
      $(document).trigger('updateContent.onafterupdate', ajaxBlockContainer);

      const bannerEl = document.querySelector('.banner-dangerous');

      expect(document.activeElement).toBe(bannerEl);

      $(bannerEl).trigger('blur');

      expect(bannerEl.hasAttribute('tabindex')).toBe(false);

    });

    test('If there is a div.banner-default-with-tick in the updated content, it should be focused', () => {

      document.body.innerHTML = `
        <div class="ajax-block-container">
        </div>`;

      const ajaxBlockContainer = document.querySelector('.ajax-block-container');

      (new FocusBanner());

      ajaxBlockContainer.innerHTML = `
        <div class="banner-default-with-tick">
          <h2>This is a problem with your upload</h2>
          <p>The file uploaded needs to be a PNG</p>
        </div>`;

      // simulate a content update event
      $(document).trigger('updateContent.onafterupdate', ajaxBlockContainer);

      const bannerEl = document.querySelector('.banner-default-with-tick');

      expect(document.activeElement).toBe(bannerEl);

      $(bannerEl).trigger('blur');

      expect(bannerEl.hasAttribute('tabindex')).toBe(false);

    });

  });

});
