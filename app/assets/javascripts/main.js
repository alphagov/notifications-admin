window.GOVUK.Frontend.initAll();

var consentData = window.GOVUK.getConsentCookie();
window.GOVUK.Modules.CookieBanner.clearOldCookies(consentData);

if (window.GOVUK.hasConsentFor('analytics', consentData)) {
  window.GOVUK.initAnalytics();
}

$(() => $("time.timeago").timeago());

$(() => GOVUK.stickAtTopWhenScrolling.init());
$(() => GOVUK.stickAtBottomWhenScrolling.init());

var showHideContent = new GOVUK.ShowHideContent();
showHideContent.init();

$(() => GOVUK.modules.start());

$(() => $('.error-message, .govuk-error-message').eq(0).parent('label').next('input').trigger('focus'));

$(() => $('.banner-dangerous').eq(0).trigger('focus'));

$(() => $('.govuk-header__container').on('click', function() {
  $(this).css('border-color', '#005ea5');
}));
