
if (document.body.classList.contains('govuk-frontend-supported')) {

  $(() => GOVUK.stickAtTopWhenScrolling.init());
  $(() => GOVUK.stickAtBottomWhenScrolling.init());
  $(() => GOVUK.notifyModules.start());

}
