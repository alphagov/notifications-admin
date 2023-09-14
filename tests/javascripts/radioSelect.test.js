const helpers = require('./support/helpers');

beforeAll(() => {
  require('../../app/assets/javascripts/radioSelect.js');

  // The sticky JS should be called whenever the times are shown so stub it out as a mock
  window.GOVUK.stickAtBottomWhenScrolling = {
    recalculate: jest.fn(() => {})
  };
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('RadioSelect', () => {
  const DAYS = [
    'Today',
    'Tomorrow',
    'Friday',
    'Saturday'
  ];
  const HOURS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
  const scrollPosition = 504;
  let originalOptionsForAllDays;
  let screenMock;

  const getDataFromOption = (option) => {
    return {
              value: option.querySelector('input').getAttribute('value'),
              label: option.querySelector('label').textContent.trim()
           };
  };

  beforeEach(() => {
    screenMock = new helpers.ScreenMock(jest);
    screenMock.setWindow({
      scrollTop: scrollPosition
    });

    const options = () => {
      let result = '';
      let optionIdx = 0;

      const getHourLabel = (hour) => {
        let label = hour;

        if (hour === 12) {
          return 'midday';
        }

        if (hour === 24) {
          return 'midnight';
        }

        return `${hour}${hour > 12 ? 'am' : 'pm'}`;
      };

      const hours = (day, start) => {
        let result = '';
        let hours = HOURS;
        let dayAsNumber = {
          'Today': 22,
          'Tomorrow': 23,
          'Friday': 24,
          'Saturday': 25
        }[day];

        if (start !== undefined) {
          hours = hours.slice(start - 1);
        }

        hours.forEach((hour, idx) => {
          const hourLabel = getHourLabel(hour);

          optionIdx++;

          result +=
            `<div class="govuk-radios__item">
              <input class="govuk-radios__input" id="scheduled_for-${optionIdx}" name="scheduled_for" type="radio" value="2019-05-${dayAsNumber}T${hour}:00:00.459156">
              <label class="govuk-label govuk-radios__label" for="scheduled_for-${optionIdx}">
                ${day} at ${hourLabel}
              </label>
            </div>`;
        });

        return result;
      };

      DAYS.forEach((day, idx) => {
        if (idx === 0) {
          result += hours(day, 11);
        } else {
          result += hours(day);
        }

        return result;
      });

      return result;
    };

    document.body.innerHTML = `
      <form method="post" enctype="multipart/form-data" action="/services/6658542f-0cad-491f-bec8-ab8457700ead/start-job/ab3080c8-f2d1-4524-b199-9718ecf6eabc">
        <fieldset>
          <legend class="form-label">
            When should Notify send these messages?
          </legend>
          <div class="radio-select" data-notify-module="radio-select" data-days="${DAYS.join(',')}">
            <div class="govuk-radios__item">
              <input class="govuk-radios__input" checked="" id="scheduled_for-0" name="scheduled_for" type="radio" value="">
              <label class="govuk-label govuk-radios__label" for="scheduled_for-0">
                Now
              </label>
            </div>
            ${options()}
          </div>
        </fieldset>
        <button class="govuk-button" data-module="govuk-button">Send 6 emails</button>
      </form>`;

      originalOptionsForAllDays = Array.from(document.querySelectorAll('.govuk-radios__item:not(:first-of-type)'))
                                          .map(option => getDataFromOption(option));

      window.GOVUK.notifyModules.start();
  });

  afterEach(() => {
    document.body.innerHTML = '';

    window.GOVUK.stickAtBottomWhenScrolling.recalculate.mockClear();
    window.scrollTo.mockClear();
  });

  describe("when the page has loaded", () => {

    test("it should show the right time and set the right name:value pairing in the form data", () => {

      const visibleField = document.querySelector('.radio-select__selected-day-and-time');
      const formData = new FormData(visibleField.form);

      expect(visibleField.value).toEqual('Now');

      expect(formData.get('scheduled_for')).toEqual('') // Now has an empty value;

    });

    test("all times originally in the page should be present and split by day", () => {

      originalOptionsForAllDays.forEach(option => {

        const radioWithValue = document.querySelector(`input[value="${option.value}"]`);
        let labelForRadio;

        expect(radioWithValue).not.toBeNull();

        labelForRadio = document.querySelector(`label[for=${radioWithValue.getAttribute('id')}]`);

        expect(labelForRadio).not.toBeNull();
        expect(labelForRadio.textContent.trim()).toEqual(option.label);

      });

    });

    test("it should have a button that shows or hides a section for choosing a time", () => {

      const expanderButton = document.querySelector('.radio-select__expander');
      let expandingSection;

      expect(expanderButton.getAttribute('aria-expanded')).toEqual('false');
      expect(expanderButton.hasAttribute('aria-controls')).toBe(true);

      expect(
        document.getElementById(expanderButton.getAttribute('aria-controls'))
      ).not.toBeNull();

    });

    test("the section for choosing a time should be collapsed", () => {

      const expandingSection = document.getElementById(
        document.querySelector('.radio-select__expander').getAttribute('aria-controls')
      );

      expect(expandingSection.hasAttribute('hidden')).toBe(true);

    });

  });

  describe("When you click the button to expand the section for choosing a time", () => {

    let expanderButton;
    let expandingSection;
    let daysView;
    let timesView;

    beforeEach(() => {

      expanderButton = document.querySelector('.radio-select__expander');
      expandingSection = document.getElementById(expanderButton.getAttribute('aria-controls'));
      daysView = expandingSection.querySelector('.radio-select__days').parentElement;
      timesView = expandingSection.querySelector('.radio-select__times').parentElement;

      helpers.triggerEvent(expanderButton, 'click');

    });

    test("the expanding section for choosing a time should show", () => {

      expect(expandingSection.hasAttribute('hidden')).toBe(false);

    });

    test("the buttons for choosing the day should be shown and match those set in the component config", () => {

      const daysSetInConfig = document.querySelector('[data-notify-module=radio-select]').dataset.days.split(',');
      let daysFromButtons;

      expect(daysView.hasAttribute('hidden')).toBe(false);

      daysFromButtons = Array.from(expandingSection.querySelectorAll('.radio-select__days button[type=button]'))
                              .map(button => button.textContent.trim());

      daysSetInConfig.forEach(day => expect(daysFromButtons).toContain(day));

    });

    test("the buttons for choosing the time should be hidden", () => {

      expect(timesView.hasAttribute('hidden')).toBe(true);

    });

    test("if you click the button that expands the section again, it should collapse the section", () => {

      helpers.triggerEvent(expanderButton, 'click');

      expect(expanderButton.getAttribute('aria-expanded')).toEqual('false');
      expect(expandingSection.hasAttribute('hidden')).toBe(true);

    });

  });

  describe("When you click the button for a day", () => {

    let expanderButton;
    let expandingSection;
    let buttonForTomorrow;
    let daysView;
    let timesView;
    let stickyJsRecalculateMock;

    beforeEach(() => {

      expanderButton = document.querySelector('.radio-select__expander');
      expandingSection = document.getElementById(expanderButton.getAttribute('aria-controls'));
      daysView = expandingSection.querySelector('.radio-select__days').parentElement;
      timesView = expandingSection.querySelector('.radio-select__times').parentElement;
      buttonForTomorrow = daysView.querySelectorAll('button[type=button]')[1];

      helpers.triggerEvent(expanderButton, 'click');
      helpers.triggerEvent(buttonForTomorrow, 'click');

    });

    test("the days view should be hidden", () => {

      expect(daysView.hasAttribute('hidden')).toBe(true);

    });

    test("the times view and the times for that day should show", () => {

      expect(timesView.hasAttribute('hidden')).toBe(false);

    });

    test("the times view should be focused", () => {

      expect(document.activeElement).toBe(timesView);

    });

    test("it should stop the browser scrolling the page when the times view is focused", () => {
      // Different browsers scroll to show the currently focused element in different ways, so it isn't out of the viewport.
      // The times view is often too tall for the viewport so the browser may often scroll to try and accommodate.
      // In our case, this is more confusing that helpful and retaining the current scroll position is better, to match
      // that of the days view we came from.
      // We do that by caching the scroll position before we switch views and reset to that afterwards, all quickly enough
      // to not be noticable
      //
      // Note: we have mocked window.scrollTo so the page will not actually scroll here.

      debugger;
      expect(window.scrollTo).toHaveBeenCalled();
      expect(window.scrollTo.mock.lastCall[1]).toEqual(scrollPosition); // window.scrollTo gets called with x,y params
    });

    test("there should be a link to return to the days view", () => {

      const backLink = expandingSection.querySelector('.radio-select__times').parentElement.querySelector('.govuk-back-link');

      expect(backLink).not.toBeNull();
      expect(backLink.textContent.trim()).toEqual('Back to days');

    });

    test("the radios should have a hidden legend and help text to give context for screen reader users", () => {

      helpers.triggerEvent(buttonForTomorrow, 'click');

      const fieldsetForRadios = timesView.querySelector('fieldset.radio-select__times:not([hidden])');
      const legend = fieldsetForRadios.querySelector('legend');
      const helpText = fieldsetForRadios.querySelector('.radio-select__times-help');

      expect(legend).not.toBeNull();
      expect(legend.classList.contains('govuk-visually-hidden')).toBe(true);
      expect(helpText).not.toBeNull();

      // help text should be set as the description for the fieldset with WAI ARIA
      expect(fieldsetForRadios.getAttribute('aria-describedby')).toEqual(helpText.getAttribute('id'));

    });

    test("the 'confirm' button container should be made sticky", () => {

      const container = expandingSection.querySelector('.radio-select__confirm');

      expect(container.classList.contains('js-stick-at-bottom-when-scrolling')).toBe(true);
      expect(GOVUK.stickAtBottomWhenScrolling.recalculate).toHaveBeenCalled();

    });

    test("if you select a time but don't confirm it and collapse the section, neitherthe field or form data should be updated", () => {

      expandingSection.querySelectorAll('.radio-select__times input[name=times-for-tomorrow]')[2].checked = true;

      helpers.triggerEvent(expanderButton, 'click');

      expect(expanderButton.getAttribute('aria-expanded')).toEqual('false');
      expect(expandingSection.hasAttribute('hidden')).toBe(true);

      const formData = new FormData(expanderButton.form);

      expect(document.querySelector('.radio-select__selected-day-and-time').value).toEqual('Now');
      expect(formData.get('scheduled_for')).toEqual('');

    });

  });

  describe("When you select a time and confirm", () => {

    let expanderButton;
    let expandingSection;
    let buttonForTomorrow;
    let radioFor3amTomorrow;

    beforeEach(() => {

      expanderButton = document.querySelector('.radio-select__expander');
      expandingSection = document.getElementById(expanderButton.getAttribute('aria-controls'));
      buttonForTomorrow = expandingSection.querySelectorAll('.radio-select__days button[type=button]')[1];
      radioFor3amTomorrow = expandingSection.querySelectorAll('.radio-select__times input[name=times-for-tomorrow]')[2];

      helpers.triggerEvent(expanderButton, 'click');
      helpers.triggerEvent(buttonForTomorrow, 'click');

      radioFor3amTomorrow.checked = true;
      helpers.triggerEvent(expandingSection.querySelector('.radio-select__confirm button'), 'click');

    });

    test("the times view should be hidden, the days view should show and the section containing both should be hidden", () => {

      expect(expandingSection.querySelector('.radio-select__times').parentElement.hasAttribute('hidden')).toBe(true);
      expect(expandingSection.querySelector('.radio-select__days').parentElement.hasAttribute('hidden')).toBe(false);
      expect(expandingSection.hasAttribute('hidden')).toBe(true);
      expect(expanderButton.getAttribute('aria-expanded')).toEqual('false');

    });

    test("the time chosen should show in the field and its value be updated in the form data", () => {

      const timeLabel = expandingSection.querySelector(`label[for=${radioFor3amTomorrow.id}]`).textContent.trim();
      const timeValue = radioFor3amTomorrow.value;
      const formData = new FormData(radioFor3amTomorrow.form);

      expect(document.querySelector('.radio-select__selected-day-and-time').value).toEqual(timeLabel);
      expect(formData.get('scheduled_for')).toEqual(timeValue);

    });

    test("the part of the field showing the time should be focused", () => {

      expect(document.activeElement).toBe(document.querySelector('.radio-select__selected-day-and-time'));

    });

  });

  describe("When you click the a 'Back to days' link", () => {

    let expanderButton;
    let expandingSection;
    let daysView;
    let timesView;
    let buttonForTomorrow;
    let backLink;

    beforeEach(() => {

      expanderButton = document.querySelector('.radio-select__expander');
      expandingSection = document.getElementById(expanderButton.getAttribute('aria-controls'));
      daysView = expandingSection.querySelector('.radio-select__days').parentElement;
      timesView = expandingSection.querySelector('.radio-select__times').parentElement;
      buttonForTomorrow = expandingSection.querySelectorAll('.radio-select__days button[type=button]')[1];
      backLink = expandingSection.querySelector('.govuk-back-link');

      helpers.triggerEvent(expanderButton, 'click');
      helpers.triggerEvent(buttonForTomorrow, 'click');
      helpers.triggerEvent(backLink, 'click');

    });

    test("the times view should be hidden", () => {

      expect(timesView.hasAttribute('hidden')).toBe(true);

    });

    test("the days view should show", () => {

      expect(daysView.hasAttribute('hidden')).toBe(false);

    });

    test("the button for the day you clicked before should be focused", () => {

      expect(document.activeElement).toBe(buttonForTomorrow);

    });

  });

});
