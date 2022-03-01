(function (global) {

  'use strict';

  $ = global.jQuery;

  let branding_style = $('.govuk-radios__item input[name="branding_style"]:checked');

  if (!branding_style.length) { return; }

  branding_style = branding_style.val();

  const $paneWrapper = $('<div class="govuk-grid-column-full"></div>');
  const $form = $('form');
  const previewType = $form.data('previewType');
  const $previewPane = $(`<iframe src="/_${previewType}?${buildQueryString(['branding_style', branding_style])}" class="branding-preview" scrolling="no"></iframe>`);

  function buildQueryString () {
    return $.map(arguments, (val, idx) => encodeURI(val[0]) + '=' + encodeURI(val[1])).join('&');
  }

  function setPreviewPane (e) {
    const $target = $(e.target);
    if ($target.attr('name') == 'branding_style') {
      branding_style = $target.val();
    }
    $previewPane.attr('src', `/_${previewType}?${buildQueryString(['branding_style', branding_style])}`);
  }

  $paneWrapper.append($previewPane);
  $form.find('.govuk-grid-row').eq(0).prepend($paneWrapper);
  $form.attr('action', location.pathname.replace(new RegExp(`set-${previewType}-branding$`), `preview-${previewType}-branding`));
  $form.find('button[type="submit"]').text('Save');

  $('fieldset').on('change', 'input[name="branding_style"]', setPreviewPane);
})(window);
