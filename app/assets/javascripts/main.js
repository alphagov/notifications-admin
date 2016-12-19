$(() => $("time.timeago").timeago());

$(() => GOVUK.modules.start());

$(() => new GOVUK.SelectionButtons('.block-label input'));

$(() => $('.error-message').eq(0).parent('label').next('input').trigger('focus'));

$(() => $('.banner-dangerous').eq(0).trigger('focus'));
