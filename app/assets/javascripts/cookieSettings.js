window.GOVUK = window.GOVUK || {};
window.GOVUK.Modules = window.GOVUK.Modules || {};

(function (Modules) {
  function CookieSettings () {}

  CookieSettings.prototype.start = function ($module) {
    this.$module = $module[0];

    this.$module.submitSettingsForm = this.submitSettingsForm.bind(this);

    document.querySelector('form[data-module=cookie-settings]')
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

    window.GOVUK.setConsentCookie(options);

    this.showConfirmationMessage();

    if(window.GOVUK.hasConsentFor('analytics')) {
      window.GOVUK.initAnalytics();
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

  Modules.CookieSettings = CookieSettings;
})(window.GOVUK.Modules);

