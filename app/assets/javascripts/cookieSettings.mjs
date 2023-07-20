import { NotifyModules } from './modules.mjs';
import { setConsentCookie } from './govuk/cookie-functions.mjs';
import { hasConsentFor } from './consent.mjs';
import { initAnalytics } from './analytics/init.mjs';

function CookieSettings () {}

CookieSettings.prototype.start = function ($module) {
  this.$module = $module[0];

  this.$module.submitSettingsForm = this.submitSettingsForm.bind(this);

  document.querySelector('form[data-notify-module=cookie-settings]')
    .addEventListener('submit', this.$module.submitSettingsForm);

  this.setInitialFormValues();
};

CookieSettings.prototype.setInitialFormValues = function () {
  var currentConsentCookie = window.GOVUK.getConsentCookie('consent');

  if (!currentConsentCookie) { return; }

  var radioButton;

  if (currentConsentCookie.analytics) {
    radioButton = document.querySelector('input[name=cookies-analytics][value=on]');
  } else {
    radioButton = document.querySelector('input[name=cookies-analytics][value=off]');
  }

  radioButton.checked = true;
};

CookieSettings.prototype.submitSettingsForm = function (event) {
  event.preventDefault();

  var formInputs = event.target.querySelectorAll("input[name=cookies-analytics]");
  var options = {};

  for ( var i = 0; i < formInputs.length; i++ ) {
    var input = formInputs[i];
    if (input.checked) {
      var value = input.value === "on" ? true : false;

      options.analytics = value;
      break;
    }
  }

  setConsentCookie(options);

  this.showConfirmationMessage();

  if(hasConsentFor('analytics')) {
    initAnalytics();
  }

  return false;
};

CookieSettings.prototype.showConfirmationMessage = function () {
  var confirmationMessage = document.querySelector('div[data-cookie-confirmation]');
  var previousPageLink = document.querySelector('.cookie-settings__prev-page');
  var referrer = CookieSettings.prototype.getReferrerLink();

  document.body.scrollTop = document.documentElement.scrollTop = 0;

  if (referrer && referrer !== document.location.pathname) {
    previousPageLink.href = referrer;
    previousPageLink.style.display = "block";
  } else {
    previousPageLink.style.display = "none";
  }

  confirmationMessage.style.display = "block";
};

CookieSettings.prototype.getReferrerLink = function () {
  return document.referrer ? new URL(document.referrer).pathname : false;
};

NotifyModules.CookieSettings = CookieSettings;
