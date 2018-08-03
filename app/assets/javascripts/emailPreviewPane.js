(function () {

  'use strict';

  const root = this,
      $ = this.jQuery;

  let branding_type = $('.multiple-choice input[name="branding_type"]:checked');
  let branding_style = $('.multiple-choice input[name="branding_style"]:checked');

  if (!branding_type.length || !branding_style.length) { return; }

  branding_type = branding_type.val();
  branding_style = branding_style.val();

  const $paneWrapper = $('<div class="column-full"></div>');
  const $form = $('form');
  const $previewPane = $('<iframe src="/_email?' +
                          buildQueryString(['branding_type', branding_type], ['branding_style', branding_style]) +
                          '" class="email-branding-preview"></iframe>');

  function buildQueryString () {
    return $.map(arguments, (val, idx) => encodeURI(val[0]) + '=' + encodeURI(val[1])).join('&');
  }

  function setPreviewPane (e) {
    const $target = $(e.target);
    if ($target.attr('name') == 'branding_type') {
      branding_type = $target.val();
    }
    if ($target.attr('name') == 'branding_style') {
      branding_style = $target.val();
    }
    $previewPane.attr('src', '/_email?' + buildQueryString(['branding_type', branding_type], ['branding_style', branding_style]));
  }

  $paneWrapper.append($previewPane);
  $form.find('.grid-row').eq(0).prepend($paneWrapper);
  $form.attr('action', location.pathname.replace(/set-email-branding$/, 'preview-email-branding'));
  $form.find('button[type="submit"]').text('Save');

  $('fieldset').on('change', 'input[name="branding_type"], input[name="branding_style"]', setPreviewPane);
})();
