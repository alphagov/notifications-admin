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

class RadioSelect {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$module = $module;
    this.confirmMadeSticky = false;
    this.keyCache = null;
    this.ENTER_CODE = 13;
    this.timesByDay = {};
    this.days = this.$module.dataset.days.split(',').map(day => {
      let dayValue = this.getKeyFromDayLabel(day);
      this.timesByDay[dayValue] = [];
      return {
        'value': dayValue,
        'label': day
      };
    });
    this.componentName = this.$module.querySelector('input[type=radio]').getAttribute('name');
    this.$module.querySelectorAll('label').forEach(function (label, idx) {
      let labelText = label.textContent.trim();
      let relatedRadio = label.previousElementSibling;
      let timeData = {
        'id': label.getAttribute('for'),
        'label': labelText,
        'value': relatedRadio.value
      };
      let day = this.getKeyFromDayLabel(labelText.split(' at ')[0]);

      if (idx === 0) { // Store the first time
        this.selectedTime = this.getTimeFromRadio(relatedRadio);

        // The first time's label doesn't contain its day so use the first day
        day = this.days[0].value;
      }

      timeData.name = `times-for-${day}`;
      this.timesByDay[day].push(timeData);

    }.bind(this));
    this.selectedDay = this.days[0];
    this.selectedTime = this.timesByDay[this.selectedDay.value][0];


    this.$module.innerHTML = this.getInitialHTML({
      'componentLabel': this.$module.previousElementSibling.textContent.trim(),
      'componentName': this.componentName,
      'selectedTime': this.selectedTime,
      'days': this.days,
      'times': this.timesByDay
    });

    this.$module.closest('fieldset').replaceWith(this.$module);

    this.form = this.$module.closest('form');
    this.formSubmitButton = this.form.querySelector('button:not([type=button])');

    this.bindEvents();

  }

  // Object holding all the states for the component's HTML
  getInitialHTML (params) {

    return `
      <label for="radio-select__selected-day-and-time" class="govuk-label radio-select__label">${params.componentLabel}</label>
      <div class="radio-select__selection-and-button">
        <input type="text" class="radio-select__selected-day-and-time" id="radio-select__selected-day-and-time" readonly value="${params.selectedTime.label}">
        <input type="hidden" class="radio-select__selected-value" value="${params.selectedTime.value}" name="${params.componentName}">
        <div class="radio-select__expander-and-expandee">
          <button type="button" class="govuk-button govuk-button--secondary radio-select__expander" aria-expanded="false" aria-controls="${params.componentName}-expanding-section">Choose a different time</button>
          <div class="radio-select__expandee" id="${params.componentName}-expanding-section" hidden>
            <div class="radio-select__view">
              <fieldset class="govuk-fieldset radio-select__days">
                <legend class="govuk-visually-hidden">Day to send these messages</legend>
                ${params.days.map((day) => `
                  <button class="govuk-button govuk-button--secondary radio-select__day" type="button" name="${day.value}" value="${day.value}">
                    ${day.label}
                  </button>`
                ).join('')}
              </fieldset>
            </div>
            <div class="radio-select__view" hidden>
              <a href="" class="govuk-link govuk-back-link radio-select__return-to-days js-header">Change the day</a>
              ${params.days.map((day) => `
                <fieldset class="govuk-fieldset radio-select__times" id="radio-select__times-for-${day.value}" aria-describedby="radio-select__times-help" hidden>
                  <legend class="govuk-visually-hidden">Time to send these messages</legend>
                  <p class="govuk-visually-hidden radio-select__times-help govuk-body" id="radio-select__times-help">Choose a time and confirm</p>
                  ${params.times[day.value].map((time) => `
                    <div class="govuk-radios__item">
                      <input class="govuk-radios__input radio-select__time" type="radio" value="${time.value}" id="${time.id}" name="${time.name}"${time.checked ? ' checked' : ''} />
                      <label class="govuk-label govuk-radios__label" for="${time.id}">${time.label}</label>
                    </div>`
                  ).join('')}
              </fieldset>`
              ).join('')}
              <div class="radio-select__confirm js-stick-at-bottom-when-scrolling">
                <button type="button" class="govuk-button govuk-button--secondary radio-select__confirm__button">Confirm time</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  bindEvents() {
    this.$module.addEventListener('click', this.handleClick.bind(this));
    this.$module.addEventListener('change', this.handleTimeSelection.bind(this));
    this.$module.addEventListener('keydown', (e) => {
      if (e.target.classList.contains('radio-select__time') || e.target.classList.contains('radio-select__selected-day-and-time')) {
        this.onEnterKeyUpAndDown(e);
      }
    });
    this.$module.addEventListener('keyup', (e) => {
      if (e.target.classList.contains('radio-select__time') || e.target.classList.contains('radio-select__selected-day-and-time')) {
        this.onEnterKeyUpAndDown(e);
      }
    });
  }

  handleClick(event) {
    const target = event.target;

    switch (true) {
      case Boolean(target.closest('.radio-select__expander')):
        event.preventDefault();
        this.toggleExpandingSection();
        break;

      case Boolean(target.closest('.radio-select__day')):
        this.handleDayClick(target);
        break;

      case Boolean(target.closest('.radio-select__return-to-days')):
        event.preventDefault();
        this.handleReturnToDays();
        break;

      case Boolean(target.closest('.radio-select__confirm__button')):
        this.selectDayAndTime();
        break;
    }
  }

  handleDayClick(dayButton) {
    this.selectedDay = dayButton.value.trim();
    this.showTimesForDay(this.selectedDay);
    this.showTimesView();
    this.focusSelectedTimeOrFirst();
  }

  handleReturnToDays() {
    this.showDaysView();
    this.$module.querySelector(`.radio-select__days button[name=${this.selectedDay}]`).focus();
  }

  handleTimeSelection(event) {
    if (!event.target.classList.contains('radio-select__time')) return;
    
    // Uncheck any other selected radios, as they don't share a name attribute
    this.$module.querySelectorAll('.radio-select__time:checked').forEach(radio => {
      if (radio !== event.target) {
        radio.checked = false;
      }
    });
  }

  showDaysView() {
    const viewPanes = this.$module.querySelectorAll('.radio-select__expandee .radio-select__view');
    viewPanes[0].removeAttribute('hidden');
    viewPanes[1].setAttribute('hidden', '');
  };

  showTimesForDay(day) {
    this.$module.querySelectorAll('.radio-select__times').forEach(timesGroup => {
      if (timesGroup.id === `radio-select__times-for-${day}`) {
        timesGroup.removeAttribute('hidden');
      } else {
        timesGroup.setAttribute('hidden', '');
      }
    });
  }

  showTimesView() {
    const viewPanes = this.$module.querySelectorAll('.radio-select__expandee .radio-select__view');

    viewPanes[0].setAttribute('hidden', '');
    viewPanes[1].removeAttribute('hidden');

    if (window.GOVUK.stickAtBottomWhenScrolling) {
      window.GOVUK.stickAtBottomWhenScrolling.recalculate();
    }
  }

  selectDayAndTime() {
    const selectedRadio = this.$module.querySelector('.radio-select__times:not([hidden]) .radio-select__time:checked');
    if (selectedRadio === null) return;

    this.selectedTime = this.getTimeFromRadio(selectedRadio);

    this.showDaysView();
    this.toggleExpandingSection();
    this.updateSelection();
    this.$module.querySelector('.radio-select__selected-day-and-time').focus();
  }

  toggleExpandingSection() {
    const expander = this.$module.querySelector('.radio-select__expander');
    const expandee = this.$module.querySelector('.radio-select__expandee');
    const isExpanded = expander.getAttribute('aria-expanded') === 'true';

    if (isExpanded) {
      expander.setAttribute('aria-expanded', 'false');
      expandee.setAttribute('hidden', '');
    } else {
      expander.setAttribute('aria-expanded', 'true');
      expandee.removeAttribute('hidden');
    }

    this.toggleFormSubmit();
  }

  toggleFormSubmit() {
    const $form = this.$module.closest('form');
    const formSubmitButton = $form.querySelector('.govuk-button:not([type=button])');

    if (!formSubmitButton.hasAttribute('hidden')) {
      formSubmitButton.style.display = 'none';
      formSubmitButton.setAttribute('hidden', '');
      $form.addEventListener('submit', this.cancelFiredEvent);
    } else {
      formSubmitButton.removeAttribute('style');
      formSubmitButton.removeAttribute('hidden');
      $form.removeEventListener('submit', this.cancelFiredEvent);
    }
  }

  focusSelectedTimeOrFirst () {
    const selector = `.radio-select__expandee input[name=times-for-${this.selectedDay}]`;
    let timeInput = this.$module.querySelector(`${selector}:checked`) || this.$module.querySelector(selector);
    timeInput.focus();
  };

  updateSelection() {
    this.$module.querySelector('.radio-select__selected-day-and-time').value = this.selectedTime.label;
    this.$module.querySelector('.radio-select__selected-value').value = this.selectedTime.value;
  }

  onEnterKeyUpAndDown(event) {
    let isExpanded;
    let targetIsSelectedDayAndTimeField;

    if (event.which !== this.ENTER_CODE) {
      return;
    }
    if (event.type === 'keydown') {
      this.keyCache = event.target;
      return;
    }

    if (event.target !== this.keyCache) {
      return;
    }

    // event.type is 'keyup', key is enter and was the key that fired the last 'keydown' event
    targetIsSelectedDayAndTimeField = event.target.classList.contains('radio-select__selected-day-and-time');
    isExpanded = this.$module.querySelector('.radio-select__expander').getAttribute('aria-expanded') === 'true';

    if (targetIsSelectedDayAndTimeField) {
      if (isExpanded) { 
        this.toggleExpandingSection();
      }
    } else { // target element is the radio for a time
      this.selectDayAndTime();
    }

    this.keyCache = null;
  }

  getTimeFromRadio (radio) {
    return {
      'value': radio.value,
      'label': radio.nextElementSibling.textContent.trim()
    };
  }

  getKeyFromDayLabel(label) {
    return label.toLowerCase().replace(/\s/g, '-');
  }

  cancelFiredEvent(evt) {
    evt.preventDefault();
  }
}

export default RadioSelect;
