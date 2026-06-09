import { isSupported } from 'govuk-frontend';
import { stickAtBottomWhenScrolling } from './stick-to-window-when-scrolling.mjs';

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
    this.componentLabelText = this.$module.previousElementSibling.textContent.trim();
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

    const initialHTML = this.buildInitialHTML({
      'componentName': this.componentName,
      'selectedTime': this.selectedTime,
      'days': this.days,
      'times': this.timesByDay
    }, this.componentLabelText);

    // clear out the original HTML structure
    this.$module.textContent = ''; 
    // append new markup
    this.$module.append(initialHTML);

    this.$module.closest('fieldset').replaceWith(this.$module);

    this.form = this.$module.closest('form');
    this.formSubmitButton = this.form.querySelector('button:not([type=button])');

    this.bindEvents();

  }

  // Object holding all the states for the component's HTML
  buildInitialHTML(params, labelText) {
    const fragment = document.createDocumentFragment();

    const $sendNowInputLabel = document.createElement('label');
    $sendNowInputLabel.setAttribute('for', 'radio-select__selected-day-and-time');
    $sendNowInputLabel.className = 'govuk-label radio-select__label';
    $sendNowInputLabel.textContent = labelText;
    fragment.appendChild($sendNowInputLabel);

    const $radioSelectContainer = document.createElement('div');
    $radioSelectContainer.className = 'radio-select__selection-and-button';

    const $sendNowInput = document.createElement('input');
    $sendNowInput.type = 'text';
    $sendNowInput.className = 'radio-select__selected-day-and-time';
    $sendNowInput.id = 'radio-select__selected-day-and-time';
    $sendNowInput.readOnly = true;
    $sendNowInput.value = params.selectedTime.label;
    $radioSelectContainer.appendChild($sendNowInput);

    const $hiddenInput = document.createElement('input');
    $hiddenInput.type = 'hidden';
    $hiddenInput.className = 'radio-select__selected-value';
    $hiddenInput.value = params.selectedTime.value;
    $hiddenInput.name = params.componentName;
    $radioSelectContainer.appendChild($hiddenInput);

    const $expanderContainer = document.createElement('div');
    $expanderContainer.className = 'radio-select__expander-and-expandee';

    const $expanderBtn = document.createElement('button');
    $expanderBtn.type = 'button';
    $expanderBtn.className = 'govuk-button govuk-button--secondary radio-select__expander';
    $expanderBtn.setAttribute('aria-expanded', 'false');
    $expanderBtn.setAttribute('aria-controls', `${params.componentName}-expanding-section`);
    $expanderBtn.textContent = 'Choose a different time';
    $expanderContainer.appendChild($expanderBtn);

    const $expandeeContainer = document.createElement('div');
    $expandeeContainer.className = 'radio-select__expandee';
    $expandeeContainer.id = `${params.componentName}-expanding-section`;
    $expandeeContainer.hidden = true;

    const $daysContainer = document.createElement('div');
    $daysContainer.className = 'radio-select__view';

    const $daysFieldset = document.createElement('fieldset');
    $daysFieldset.className = 'govuk-fieldset radio-select__days';

    const $daysLegend = document.createElement('legend');
    $daysLegend.className = 'govuk-visually-hidden';
    $daysLegend.textContent = 'Day to send these messages';
    $daysFieldset.appendChild($daysLegend);

    params.days.forEach(day => {
      const $dayBtn = document.createElement('button');
      $dayBtn.className = 'govuk-button govuk-button--secondary radio-select__day';
      $dayBtn.type = 'button';
      $dayBtn.name = day.value;
      $dayBtn.value = day.value;
      $dayBtn.textContent = day.label;
      $daysFieldset.appendChild($dayBtn);
    });

    $daysContainer.appendChild($daysFieldset);
    $expandeeContainer.appendChild($daysContainer);

    const $dayTimesContainer = document.createElement('div');
    $dayTimesContainer.className = 'radio-select__view';
    $dayTimesContainer.hidden = true;

    const $backLink = document.createElement('a');
    $backLink.href = '';
    $backLink.className = 'govuk-link govuk-back-link radio-select__return-to-days js-header';
    $backLink.textContent = 'Change the day';
    $dayTimesContainer.appendChild($backLink);

    params.days.forEach(day => {
      const $dayTimesFieldset = document.createElement('fieldset');
      $dayTimesFieldset.className = 'govuk-fieldset radio-select__times';
      $dayTimesFieldset.id = `radio-select__times-for-${day.value}`;
      $dayTimesFieldset.setAttribute('aria-describedby', 'radio-select__times-help');
      $dayTimesFieldset.hidden = true;

      const $dayTimesLegend = document.createElement('legend');
      $dayTimesLegend.className = 'govuk-visually-hidden';
      $dayTimesLegend.textContent = 'Time to send these messages';
      $dayTimesFieldset.appendChild($dayTimesLegend);

      const $timesHint = document.createElement('p');
      $timesHint.className = 'govuk-visually-hidden radio-select__times-help govuk-body';
      $timesHint.id = 'radio-select__times-help';
      $timesHint.textContent = 'Choose a time and confirm';
      $dayTimesFieldset.appendChild($timesHint);

      params.times[day.value].forEach(time => {
        const $radioItemContainer = document.createElement('div');
        $radioItemContainer.className = 'govuk-radios__item';

        const $radioInput = document.createElement('input');
        $radioInput.className = 'govuk-radios__input radio-select__time';
        $radioInput.type = 'radio';
        $radioInput.value = time.value;
        $radioInput.id = time.id;
        $radioInput.name = time.name;
        if (time.checked) {
          $radioInput.checked = true;
        }
        $radioItemContainer.appendChild($radioInput);

        const $radioTimeLabel = document.createElement('label');
        $radioTimeLabel.className = 'govuk-label govuk-radios__label';
        $radioTimeLabel.setAttribute('for', time.id);
        $radioTimeLabel.textContent = time.label;
        $radioItemContainer.appendChild($radioTimeLabel);

        $dayTimesFieldset.appendChild($radioItemContainer);
      });

      $dayTimesContainer.appendChild($dayTimesFieldset);
    });

    const $confirmContainer = document.createElement('div');
    $confirmContainer.className = 'radio-select__confirm js-stick-at-bottom-when-scrolling';

    const $confirmTimeBtn = document.createElement('button');
    $confirmTimeBtn.type = 'button';
    $confirmTimeBtn.className = 'govuk-button govuk-button--secondary radio-select__confirm__button';
    $confirmTimeBtn.textContent = 'Confirm time';
    $confirmContainer.appendChild($confirmTimeBtn);

    $dayTimesContainer.appendChild($confirmContainer);
    $expandeeContainer.appendChild($dayTimesContainer);

    $expanderContainer.appendChild($expandeeContainer);
    $radioSelectContainer.appendChild($expanderContainer);
    fragment.appendChild($radioSelectContainer);

    return fragment;
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

    stickAtBottomWhenScrolling.recalculate();
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
