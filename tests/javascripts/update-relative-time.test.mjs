import { jest } from '@jest/globals';
import UpdateRelativeTime from '../../app/assets/javascripts/esm/update-relative-time.mjs';

describe('UpdateRelativeTime', () => {
  const selector = '[data-notify-module="update-relative-time"]';
  const currentYear = new Date().getFullYear();
  const previousYear = currentYear - 1;
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
    // fix to mid-month for all offset calculations
    // we now that JS module Intl.Date works as expected
    // so in these tests we want to avoid doing JS month
    // substractions and fixes for days with 31 months
    now = new Date(`${currentYear}-07-15T12:00:00Z`); 
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

  describe('on page load', () => {
    test('halts if datetime attribute is not present on the element', () => {
      const el = document.querySelector(selector);
      el.removeAttribute('datetime');
      new UpdateRelativeTime(selector);
      expect(el.textContent).toBe('');
    });

    test('updates relative time text for all elements on the page in en-GB', () => {
      // Changed to 60s and 120s to avoid the "just now" thresholds
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
      // Set to 75s so that after a 60s advance, it is 135s (2m ago)
      dynamicEl.setAttribute('datetime', new Date(jest.now() - 75000).toISOString());
      
      container.appendChild(dynamicEl);
      expect(dynamicEl.textContent).toBe('');

      // Advance 60s to trigger the polling interval
      jest.advanceTimersByTime(60000);

      expect(dynamicEl.textContent).toBe('2 minutes ago');
      expect(dynamicEl.hasAttribute('title')).toBe(true);
    });

    test('automatically updates the relative time text as time passes', () => {
      const el = setElementDateTime(10000); // 10s ago
      new UpdateRelativeTime(selector);
      expect(el.textContent).toBe('just now');

      jest.advanceTimersByTime(60000); // Fast forward 1m (now 70s ago)
      expect(el.textContent).toBe('1 minute ago');
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
      { label: 'just now (under 30s)', offset: 25000, expected: 'just now' },
      { label: 'in the last minute (30s to 59s)', offset: 45000, expected: 'in the last minute' },
      { label: 'minutes (at 60s boundary)', offset: 60000, expected: '1 minute ago' },
      { label: 'hours (at 45m boundary)', offset: 45 * 60000, expected: '1 hour ago' },
      { label: 'hours (21h)', offset: 21 * 3600000, expected: '21 hours ago' },
      { label: 'yesterday (at 22h boundary)', offset: 22 * 3600000, expected: 'yesterday' },
      { label: 'days (26 days)', offset: 26 * 86400000, expected: '26 days ago' },
      { label: 'last month', offset: 30 * 86400000, expected: 'last month' },
      { label: 'last year', offset: 365 * 86400000, expected: 'last year' },
    ];

    test.each(scenarios)('displays correct text for $label', ({ offset, expected }) => {
      setElementDateTime(offset);
      new UpdateRelativeTime(selector);
      expect(document.querySelector(selector).textContent).toBe(expected);
    });
  });

  describe('calendar boundary edge cases', () => {
    

    const boundaryScenarios = [
      {
        label: '1st of the month looking at 31st (1 day ago across month boundary)',
        systemTime: `${currentYear}-08-01T12:00:00Z`,
        elementTime: `${currentYear}-07-31T12:00:00Z`,
        expected: 'yesterday'
      },
      {
        label: '1st of the month looking at 30th (2 days ago across month boundary)',
        systemTime: `${currentYear}-08-01T12:00:00Z`,
        elementTime: `${currentYear}-07-30T12:00:00Z`,
        expected: '2 days ago'
      },
      {
        label: '31st of the month looking at 1st of the SAME month (>27 days ago)',
        systemTime: `${currentYear}-07-31T12:00:00Z`,
        elementTime: `${currentYear}-07-01T12:00:00Z`,
        expected: 'this month'
      },
      {
        label: '30th of the month looking at 1st of the SAME month (>27 days ago)',
        systemTime: `${currentYear}-11-30T12:00:00Z`,
        elementTime: `${currentYear}-11-01T12:00:00Z`,
        expected: 'this month'
      },
      {
        label: '1st of the month looking at 1st of the PREVIOUS month (~30 days ago)',
        systemTime: `${currentYear}-08-01T12:00:00Z`,
        elementTime: `${currentYear}-07-01T12:00:00Z`,
        expected: 'last month'
      },
      {
        label: '1st Jan looking back at 31st Dec (1 day ago at turn of the year)',
        systemTime: `${currentYear}-01-01T12:00:00Z`,
        elementTime: `${previousYear}-12-31T12:00:00Z`,
        expected: 'yesterday'
      },
      {
        label: '15th Jan looking back at 15th Dec (1 month ago across turn of the year)',
        systemTime: `${currentYear}-01-15T12:00:00Z`,
        elementTime: `${previousYear}-12-15T12:00:00Z`,
        expected: 'last month'
      },
      {
        label: '1st Jan looking back at 1st Jan of previous year (1 year ago)',
        systemTime: `${currentYear}-01-01T12:00:00Z`,
        elementTime: `${previousYear}-01-01T12:00:00Z`,
        expected: 'last year'
      },
      {
        label: 'March 1st looking back at Feb 29th in a leap year (1 day ago / yesterday)',
        systemTime: '2024-03-01T12:00:00Z',
        elementTime: '2024-02-29T12:00:00Z',
        expected: 'yesterday'
      },
      {
        label: 'March 1st looking back at Feb 28th in a leap year (2 days ago)',
        systemTime: '2024-03-01T12:00:00Z',
        elementTime: '2024-02-28T12:00:00Z',
        expected: '2 days ago'
      },
      {
        label: 'March 1st 2025 looking back at March 1st 2024 across a 366-day leap year (1 year ago)',
        systemTime: '2025-03-01T12:00:00Z',
        elementTime: '2024-03-01T12:00:00Z',
        expected: 'last year'
      }
    ];

    test.each(boundaryScenarios)('displays correct text for $label', ({ systemTime, elementTime, expected }) => {
      jest.setSystemTime(new Date(systemTime).getTime());
      
      const el = document.querySelector(selector);
      el.setAttribute('datetime', new Date(elementTime).toISOString());
      
      new UpdateRelativeTime(selector);
      expect(el.textContent).toBe(expected);
    });
  });
});
