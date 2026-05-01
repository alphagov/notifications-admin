
if (document.body.classList.contains('govuk-frontend-supported')) {

  $(() => GOVUK.notifyModules.start());

  $(() => $('.error-message, .govuk-error-message').eq(0).parent('label').next('input').trigger('focus'));
}
