import { jest } from '@jest/globals';
import UpdateRelativeTime from '../../app/assets/javascripts/esm/update-relative-time.mjs';

describe('UpdateRelativeTime', () => {
  const selector = '[data-notify-module="update-relative-time"]'
  let now;

  beforeEach(() => {
    jest.resetModules();
    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <div id="container">
        <time data-notify-module="update-relative-time"></time>
      </div>
    `;

    jest.useFakeTimers();
    now = new Date(); 
    jest.setSystemTime(now.getTime());
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    document.body.innerHTML = '';
  });

  const setElementDateTime = (offsetMs) => {
    const el = document.querySelector(selector);
    const date = new Date(jest.now() - offsetMs);
    el.setAttribute('datetime', date.toISOString());
    return el;
  };

  const getCalendarOffset = (unit, value) => {
    const d = new Date(jest.now());
    if (unit === 'month') d.setMonth(d.getMonth() - value);
    if (unit === 'year') d.setFullYear(d.getFullYear() - value);
    return jest.now() - d.getTime();
  };

  describe('on page load', () => {
    test('halts if datetime attribute is not present on the element', () => {
      const el = document.querySelector(selector);
      el.removeAttribute('datetime');
      new UpdateRelativeTime(selector);
      expect(el.textContent).toBe('');
    });

    test('updates relative time text for all elements on the page in en-GB', () => {
      document.body.innerHTML = `
        <time data-notify-module="update-relative-time" datetime="${new Date(jest.now() - 60000).toISOString()}"></time>
        <time data-notify-module="update-relative-time" datetime="${new Date(jest.now() - 120000).toISOString()}"></time>
      `;
      new UpdateRelativeTime(selector);
      
      const elements = document.querySelectorAll(selector);
      expect(elements[0].textContent).toBe('1 minute ago');
      expect(elements[1].textContent).toBe('2 minutes ago');
    });

    test('sets a human-readable title attribute text in en-GB', () => {
      const el = setElementDateTime(0);
      new UpdateRelativeTime(selector);
      
      const expectedTitle = new Intl.DateTimeFormat('en-GB', {
        dateStyle: 'long',
        timeStyle: 'short'
      }).format(new Date(jest.now()));

      expect(el.getAttribute('title')).toBe(expectedTitle);
    });
  });

  describe('for dynamically added elements', () => {
    test('picks up elements added to the DOM after the next interval tick', () => {
      new UpdateRelativeTime(selector);
      const container = document.getElementById('container');
      
      const dynamicEl = document.createElement('time');
      dynamicEl.setAttribute('data-notify-module', 'update-relative-time');
      dynamicEl.setAttribute('datetime', new Date(jest.now() - 75000).toISOString());
      
      container.appendChild(dynamicEl);
      expect(dynamicEl.textContent).toBe('');

      // Advance 60s to trigger the polling interval
      jest.advanceTimersByTime(60000);

      expect(dynamicEl.textContent).toBe('2 minutes ago');
      expect(dynamicEl.hasAttribute('title')).toBe(true);
    });

    test('automatically updates the relative time text as time passes', () => {
      const el = setElementDateTime(40000); // 40s ago
      new UpdateRelativeTime(selector);
      expect(el.textContent).toBe('40 seconds ago');

      jest.advanceTimersByTime(60000); // Fast forward 1m
      expect(el.textContent).toBe('2 minutes ago');
    });

    test('does not trigger a DOM update if the text content remains the same', () => {
      const el = setElementDateTime(3600000 * 5); // 5 hours ago
      new UpdateRelativeTime(selector);
      
      const spy = jest.spyOn(el, 'textContent', 'set');
      
      // 5h 1m still rounds to "5 hours"
      jest.advanceTimersByTime(60000); 
      
      expect(spy).not.toHaveBeenCalled();
    });
  });

  describe('text shows correct units for specific elapsed time threshold', () => {
    const scenarios = [
      { label: 'seconds (under 45s)', offset: 40000, expected: '40 seconds ago' },
      { label: 'minutes (at 45s boundary)', offset: 45000, expected: '1 minute ago' },
      { label: 'hours (at 45m boundary)', offset: 45 * 60000, expected: '1 hour ago' },
      { label: 'hours (21h)', offset: 21 * 3600000, expected: '21 hours ago' },
      { label: 'yesterday (at 22h boundary)', offset: 22 * 3600000, expected: 'yesterday' },
      { label: 'days (26 days)', offset: 26 * 86400000, expected: '26 days ago' },
      { label: 'last month', offset: getCalendarOffset('month', 1), expected: 'last month' },
      { label: 'last year', offset: getCalendarOffset('year', 1), expected: 'last year' },
    ];

    test.each(scenarios)('displays correct text for $label', ({ offset, expected }) => {
      setElementDateTime(offset);
      new UpdateRelativeTime(selector);
      expect(document.querySelector(selector).textContent).toBe(expected);
    });
  });
});