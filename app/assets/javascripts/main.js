
if (document.body.classList.contains('govuk-frontend-supported')) {
  $(() => $("time.timeago").timeago());

  $(() => GOVUK.stickAtTopWhenScrolling.init());
  $(() => GOVUK.stickAtBottomWhenScrolling.init());
  $(() => GOVUK.notifyModules.start());

  $(() => $('.error-message, .govuk-error-message').eq(0).parent('label').next('input').trigger('focus'));
}
