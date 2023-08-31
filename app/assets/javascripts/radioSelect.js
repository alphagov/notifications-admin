(function(global) {

  "use strict";

  var Modules = global.GOVUK.NotifyModules;

  // Object holding all the states for the component's HTML
  function getInitialHTML (params) {

    return `
      <label for="radio-select__selected-day-and-time" class="govuk-label radio-select__label">${params.componentLabel}</label>
      <div class="radio-select__selection-and-button">
        <input type="text" class="radio-select__selected-day-and-time" id="radio-select__selected-day-and-time" readonly value="${params.selectedTime.label}">
        <input type="hidden" class="radio-select__selected-value" value="${params.selectedTime.value}" name="${params.componentName}">
        <div class="radio-select__expander-and-expandee">
          <button type='button' class='govuk-button govuk-button--secondary radio-select__expander' aria-expanded="false" >Choose another time</button>
          <div class="radio-select__expandee" hidden>
            <div class="radio-select__column">
              <fieldset class="govuk-fieldset radio-select__days">
                <legend class="govuk-visually-hidden">Day to send these messages</legend>
                ${params.days.map((day, idx) => `
                  <button class="govuk-button govuk-button--secondary radio-select__day" type="button" name="${day.value}" value="${day.value}">
                    ${day.label}
                  </button>`
                ).join('')}
              </fieldset>
            </div>
            <div class="radio-select__column" hidden>
              <a href="" class="govuk-link govuk-back-link radio-select__return-to-days js-header">Back to days</a>
              ${params.days.map((day, idx) => `
                <fieldset class="govuk-fieldset radio-select__times" aria-describedby="radio-select__times-description" id="radio-select__times-for-${day.value}" hidden>
                  <legend class="govuk-visually-hidden">Time to send these messages</legend>
                  <p class="govuk-visually-hidden" id="radio-select__times-description">Choose a time and press confirm or cancel</p>
                  ${params.times[day.value].map((time, idx) => `
                    <div class="govuk-radios__item">
                      <input class="govuk-radios__input radio-select__time" type="radio" value="${time.value}" id="${time.id}" name="${time.name}"${time.checked ? ' checked' : ''} />
                      <label class="govuk-label govuk-radios__label" for="${time.id}">${time.label}</label>
                    </div>`
                  ).join('')}
              </fieldset>`
              ).join('')}
              <div class="radio-select__confirm js-stick-at-bottom-when-scrolling">
                <button type="button" class="govuk-button radio-select__confirm__button">Confirm time</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  Modules.RadioSelect = function() {

    this.start = function(component) {

      this.$component = $(component);
      this.confirmMadeSticky = false;

      function _getTimeFromRadio (radio) {
        return {
          'value': radio.value,
          'label': radio.nextElementSibling.textContent.trim()
        }
      };

      const timesByDay = {};

      const days = this.$component.data('days').split(',').map(day => {
        const dayValue = day.toLowerCase();

        timesByDay[dayValue] = [];

        return {
          'value': dayValue,
          'label': day
        }
      });

      const componentName = this.$component.find('input[type=radio]').attr('name');

      this.$component.find('label').each(function (idx, label) {
        const labelText = label.textContent.trim();
        const relatedRadio = label.previousElementSibling;
        const timeData = {
          'id': label.getAttribute('for'),
          'label': labelText,
          'value': relatedRadio.value
        };
        let day = labelText.split(' ')[0].toLowerCase();

        if (idx === 0) { // Store the first time
          this.selectedTime = _getTimeFromRadio(relatedRadio);

          // The first time's label doesn't contain its day so use the first day
          day = days[0].value;
        }

        timeData.name = `times-for-${day}`;
        timesByDay[day].push(timeData);

      }.bind(this));

      this.focusContainer = function ($container) {
        const onBlurContainer = evt => {
          $container
            .removeAttr('tabindex')
            .off('blur', onBlurContainer);
        };

        $container
          .attr('tabindex', 0)
          .focus()
          .on('blur', onBlurContainer);
      };

      this.showDaysView = function () {
        const viewPanes = this.$component.find('.radio-select__expandee .radio-select__column');

        viewPanes.get(0).removeAttribute('hidden');
        viewPanes.get(1).setAttribute('hidden', '');
      };

      this.showTimesView = function () {
        const viewPanes = this.$component.find('.radio-select__expandee .radio-select__column');

        viewPanes.get(0).setAttribute('hidden', '');
        viewPanes.get(1).removeAttribute('hidden');

        GOVUK.stickAtBottomWhenScrolling.recalculate();
      };

      this.showTimesForDay = function (day) {
        this.$component.find('.radio-select__expandee .radio-select__times').each((idx, timesGroup) => {
          if (timesGroup.id === `radio-select__times-for-${day}`) {
            timesGroup.removeAttribute('hidden');
          } else {
            timesGroup.setAttribute('hidden', '');
          }
        });
      };

      this.toggleFormSubmit = function () {
        const $formSubmitButton = this.$component.closest('form').find('.govuk-button:not([type=button])').eq(0);

        if ($formSubmitButton.attr('hidden') === undefined) {
          $formSubmitButton
            .hide() // needed to stop the `display` property overriding `hidden`
            .attr('hidden', '');
        } else {
          $formSubmitButton
            .show() // needed to stop the `display` property overriding `hidden`
            .removeAttr('hidden', '');
        }
      };

      this.toggleExpandingSection = function () {
        const expander = this.$component.find('.radio-select__expander').get(0);
        const expandee = this.$component.find('.radio-select__expandee').get(0);
        const isExpanded = expander.getAttribute('aria-expanded') === 'true';

        if (isExpanded) {
          expander.setAttribute('aria-expanded', 'false');
          expandee.setAttribute('hidden', '');
        } else {
          expander.setAttribute('aria-expanded', 'true');
          expandee.removeAttribute('hidden');
        }

        this.toggleFormSubmit();
      };

      this.updateSelection = function () {
        this.$component.find('.radio-select__selected-day-and-time').val(this.selectedTime.label);
        this.$component.find('.radio-select__selected-value').val(this.selectedTime.value);
      };

      this.onConfirmClick = function (event) {
        this.selectedTime = _getTimeFromRadio(
          this.$component.find('.radio-select__times:not([hidden]) .radio-select__time:checked').get(0)
        );

        if (this.selectedTime.length === 0) { return; }

        // reset state of expanding section for selecting a day + time
        this.showDaysView();
        this.toggleExpandingSection();
        this.updateSelection();
        this.$component.find('.radio-select__selected-day-and-time').focus();
      };

      this.onReturnToDaysClick = function (event) {
        event.preventDefault();

        this.showDaysView();
        this.focusContainer(
          this.$component.find('.radio-select__days').eq(0)
        );
      };

      this.onDayClick = function (event) {
        let scrollTop;

        this.selectedDay = event.target.value.trim();

        this.showTimesForDay(this.selectedDay);
        this.showTimesView();

        scrollTop = $(window).scrollTop(); // store current scroll position

        this.focusContainer(
          this.$component.find(`#radio-select__times-for-${this.selectedDay}`).eq(0)
        );

        $(window).scrollTop(scrollTop); // reset window to previous scroll position
      };

      this.onExpanderClick = function (event) {
        event.preventDefault();

        this.toggleExpandingSection();
      };

      // uncheck any radios for other days already checked
      // radios for different days don't share a name so selecting one doesn't deselect those
      // selected for other days
      this.onTimeSelection = function (event) {
        this.$component.find('.radio-select__time:checked').each((idx, radio) => {
          if (radio !== event.target) { radio.checked = false}
        });
      };

      this.selectedDay = days[0];
      this.selectedTime = timesByDay[this.selectedDay.value][0];

      this.$component.html(getInitialHTML({
        'componentLabel': this.$component.prev('legend').text().trim(),
        'componentName': componentName,
        'selectedTime': this.selectedTime,
        'days': days,
        'times': timesByDay
      }));

      this.$component.parent('fieldset').replaceWith(this.$component);

      // set events
      this.$component
        .on('click', '.radio-select__expander', this.onExpanderClick.bind(this))
        .on('click', '.radio-select__day', this.onDayClick.bind(this))
        .on('click', '.radio-select__return-to-days', this.onReturnToDaysClick.bind(this))
        .on('click', '.radio-select__confirm__button', this.onConfirmClick.bind(this))
        .on('change', '.radio-select__time', this.onTimeSelection.bind(this));

    };

  };

})(window);
