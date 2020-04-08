window.GOVUK = window.GOVUK || {};
window.GOVUK.Modules = window.GOVUK.Modules || {};

(function (Modules) {
  function CookieBanner () { }

  CookieBanner.clearOldCookies = function (consent) {
    var gaCookies = ['_ga', '_gid'];

    // clear old cookie set by our previous JS, set on the www domain
    if (window.GOVUK.cookie('seen_cookie_message')) {
      document.cookie = 'seen_cookie_message=;expires=' + new Date().toGMTString() + ';path=/';
    }

    if (consent === null) {
      for (var i = 0; i < gaCookies.length; i++) {
        if (window.GOVUK.cookie(gaCookies[i])) {
          // GA cookies are set on the base domain so need the www stripping
          var cookieString = gaCookies[i] + '=;expires=' + new Date().toGMTString() + ';domain=' + window.location.hostname.replace(/^www\./, '.') + ';path=/';
          document.cookie = cookieString;
        }
      }
    }
  };

  CookieBanner.prototype.start = function ($module) {
    this.$module = $module[0];
    this.$module.hideCookieMessage = this.hideCookieMessage.bind(this);
    this.$module.showConfirmationMessage = this.showConfirmationMessage.bind(this);
    this.$module.setCookieConsent = this.setCookieConsent.bind(this);

    this.$module.cookieBanner = document.querySelector('.notify-cookie-banner');
    this.$module.cookieBannerConfirmationMessage = this.$module.querySelector('.notify-cookie-banner__confirmation');

    this.setupCookieMessage();
  };

  CookieBanner.prototype.setupCookieMessage = function () {
    this.$hideLink = this.$module.querySelector('button[data-hide-cookie-banner]');
    if (this.$hideLink) {
      this.$hideLink.addEventListener('click', this.$module.hideCookieMessage);
    }

    this.$acceptCookiesLink = this.$module.querySelector('button[data-accept-cookies=true]');
    if (this.$acceptCookiesLink) {
      this.$acceptCookiesLink.addEventListener('click', () => this.$module.setCookieConsent(true));
    }

    this.$rejectCookiesLink = this.$module.querySelector('button[data-accept-cookies=false]');
    if (this.$rejectCookiesLink) {
      this.$rejectCookiesLink.addEventListener('click', () => this.$module.setCookieConsent(false));
    }

    this.showCookieMessage();
  };

  CookieBanner.prototype.showCookieMessage = function () {
    // Show the cookie banner if not in the cookie settings page
    if (!this.isInCookiesPage()) {
      var hasCookiesPolicy = window.GOVUK.cookie('cookies_policy');

      if (this.$module && !hasCookiesPolicy) {
        this.$module.style.display = 'block';
      }
    }
  };

  CookieBanner.prototype.hideCookieMessage = function (event) {
    if (this.$module) {
      this.$module.style.display = 'none';
    }

    if (event.target) {
      event.preventDefault();
    }
  };

  CookieBanner.prototype.setCookieConsent = function (analyticsConsent) {
    window.GOVUK.setConsentCookie({ 'analytics': analyticsConsent });

    this.$module.showConfirmationMessage(analyticsConsent);
    this.$module.cookieBannerConfirmationMessage.focus();

    if (analyticsConsent) { window.GOVUK.initAnalytics(); }
  };

  CookieBanner.prototype.showConfirmationMessage = function (analyticsConsent) {
    var messagePrefix = analyticsConsent ? 'You’ve accepted analytics cookies.' : 'You told us not to use analytics cookies.';

    this.$cookieBannerMainContent = document.querySelector('.notify-cookie-banner__wrapper');
    this.$cookieBannerConfirmationMessage = document.querySelector('.notify-cookie-banner__confirmation-message');

    this.$cookieBannerConfirmationMessage.insertAdjacentText('afterbegin', messagePrefix);
    this.$cookieBannerMainContent.style.display = 'none';
    this.$module.cookieBannerConfirmationMessage.style.display = 'block';
  };

  CookieBanner.prototype.isInCookiesPage = function () {
    return window.location.pathname === '/cookies';
  };

  Modules.CookieBanner = CookieBanner;
})(window.GOVUK.Modules);

