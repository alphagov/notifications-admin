$(() => $("time.timeago").timeago());

$(() => GOVUK.stickAtTopWhenScrolling.init());

$(() => GOVUK.modules.start());

$(() => $('.error-message').eq(0).parent('label').next('input').trigger('focus'));

$(() => $('.banner-dangerous').eq(0).trigger('focus'));
