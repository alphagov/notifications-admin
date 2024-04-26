(function (global) {

  'use strict';

  $ = global.jQuery;

  let branding_style = $('.govuk-radios__item input[name="branding_style"]:checked');

  if (!branding_style.length) { return; }

  branding_style = branding_style.val();

  const $paneWrapper = $('<div class="govuk-grid-column-full"></div>');
  const $form = $('form');
  const previewType = $form.data('previewType');
  const letterBrandingPreviewRootPath = `templates/${previewType}-preview-image`;
  const $iframePreviewPane = $(`<iframe src="/_${previewType}?${buildQueryString(['branding_style', branding_style])}" class="branding-preview" scrolling="no"></iframe>`);
  const $imagePreviewPane = $(
    `<div class="branding-preview-image">
      <img src="/${letterBrandingPreviewRootPath}?${buildQueryString(['branding_style', branding_style])}" alt="Preview of selected letter branding">
    </div>`
  );

  function buildQueryString () {
    return $.map(arguments, (val, idx) => encodeURI(val[0]) + '=' + encodeURI(val[1])).join('&');
  }

  function setPreviewPane (e) {
    const $target = $(e.target);
    if ($target.attr('name') == 'branding_style') {
      branding_style = $target.val();
    }

    if (previewType === 'letter') {
      $imagePreviewPane.find('img').attr('src', `/${letterBrandingPreviewRootPath}?${buildQueryString(['branding_style', branding_style])}`);
    } else {
      $iframePreviewPane.attr('src', `/_${previewType}?${buildQueryString(['branding_style', branding_style])}`);
    }
  }

  if (previewType === 'letter') {
    $paneWrapper.append($imagePreviewPane);
  } else {
    $paneWrapper.append($iframePreviewPane);
  }

  $form.find('.govuk-grid-row').eq(0).prepend($paneWrapper);
  $form.attr('action', location.pathname.replace(new RegExp(`set-${previewType}-branding$`), `preview-${previewType}-branding`));
  $form.find('button').text('Save');

  $('fieldset').on('change', 'input[name="branding_style"]', setPreviewPane);
})(window);
