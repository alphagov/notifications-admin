import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

// inspired by https://polypane.app/blog/the-intl-api-the-best-browser-api-youre-not-using/
class UpdateRelativeTime {
  // creating formatters is expensive so we create them once and reuse
  static relativeFormatter = new Intl.RelativeTimeFormat('en-GB', { numeric: 'auto' });
  static fullDateFormatter = new Intl.DateTimeFormat('en-GB', { dateStyle: 'long', timeStyle: 'short' });

  constructor(selector) {
    if (!isSupported()) {
      return this;  
    }

    this.selector = selector;

    this.init();
  }

  init() {
    this.updateExistingElements();
    
    // start global 60s interval
    setInterval(() => this.updateExistingElements(), 60000);
  }

  updateExistingElements() {
    const $elements = document.querySelectorAll(this.selector);
    const now = new Date();
    $elements.forEach(($el) => this.updateTextString($el, now));
  }

  updateTextString(element, currentTime) {
    const elementDatetimeStamp = element.getAttribute('datetime');
    // don't run if we forgot to include the attribute
    if (!elementDatetimeStamp) return;

    const date = new Date(elementDatetimeStamp);

    // we only update the title attribute once with
    // human-readible date format 
    if (!element.hasAttribute('title')) {
      element.setAttribute('title', UpdateRelativeTime.fullDateFormatter.format(date));
    }

    const relativeTimeString = this.calculateRelativeTimeString(date, currentTime);

    // only update text if there's a change
    // hours, days and longer don't need to have
    // their text updated every minute
    if (element.textContent !== relativeTimeString) {
      element.textContent = relativeTimeString;
    }
  }

  calculateRelativeTimeString(elementTime, currentTime) {
    // thresholds to switch display units
    // in line with what we used before and other libraries
    // https://github.com/rmm5t/jquery-timeago/blob/master/jquery.timeago.js#L102
    // https://day.js.org/docs/en/customization/relative-time#relative-time-thresholds-and-rounding
    const diffInSeconds = Math.round((elementTime - currentTime) / 1000);
    const absSeconds = Math.abs(diffInSeconds);

    if (absSeconds < 45) { // 0 to 44s
      return UpdateRelativeTime.relativeFormatter.format(diffInSeconds, 'second');
    }

    const diffInMinutes = Math.round(diffInSeconds / 60);
    if (Math.abs(diffInMinutes) < 45) { // 45s to 44m
      return UpdateRelativeTime.relativeFormatter.format(diffInMinutes, 'minute');
    }

    const diffInHours = Math.round(diffInMinutes / 60);
    if (Math.abs(diffInHours) < 22) { // 45m to 21h
      return UpdateRelativeTime.relativeFormatter.format(diffInHours, 'hour');
    }

    const diffInDays = Math.round(diffInHours / 24);
    if (Math.abs(diffInDays) < 27) { // 22h to 26d
      return UpdateRelativeTime.relativeFormatter.format(diffInDays, 'day');
    }

    // for months and years, we use the calendar date logic as lengths are different
    const monthDiff = (elementTime.getFullYear() - currentTime.getFullYear()) * 12 + 
                      (elementTime.getMonth() - currentTime.getMonth());

    if (Math.abs(monthDiff) < 11) {
      return UpdateRelativeTime.relativeFormatter.format(monthDiff, 'month');
    }

    const yearDiff = Math.round(monthDiff / 12);
    return UpdateRelativeTime.relativeFormatter.format(yearDiff, 'year');
  }
}

export default UpdateRelativeTime;
