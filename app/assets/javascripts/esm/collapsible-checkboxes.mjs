import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class CollapsibleCheckboxes  {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.toggleButtonClass = 'notify-button--with-chevron';
    this.toggleButtonChevronClass = 'notify-button--with-chevron__chevron';
    this.toggleButtonChevronActiveClass = 'notify-button--with-chevron__chevron--active';

    this.$module = $module;
    this.$selectionSummaryContainer = this.$module.querySelector('.selection-summary');
    this.fieldLabel = this.$module.getAttribute('data-field-label');
    this.$fieldset = this.$module.querySelector('.govuk-fieldset');
    this.$checkboxesContainer = this.$fieldset.querySelector('.govuk-checkboxes');
    this.$checkboxesArray = this.$fieldset.querySelectorAll('input[type=checkbox]');
    this.legendText = this.$fieldset.querySelector('legend').textContent.trim();

    this.total = this.$checkboxesArray.length;
    this.selectionSummaryContent = {
      all: (selection, total, field) => `All ${field}s`,
      some: (selection, total, field) => `${selection} of ${total} ${field}s`,
      none: (selection, total, field) => ({
        "folder": "No folders (only templates outside a folder)",
        "team member": "No team members (only you)"
      }[field] || `No ${field}s`)
    };

    // add heading
    this.addHeadingHideLegend();

    // insert selection summary text
    this.initSelectionSummary();

    // insert toggle button
    this.constructToggleButton();

    // add custom classes
    this.$fieldset.classList.add('selection-wrapper');
    this.$checkboxesContainer.classList.add('selection-content', 'govuk-!-margin-top-3');

    // hide checkboxes inside the fieldset
    this.$fieldset.setAttribute('hidden', '');

    this.handleToggleButtonClick();
    this.handleCheckboxClick();
  }

  constructToggleButton() {
    const $toggleButton = document.createElement('button');
    $toggleButton.setAttribute('type', 'button');
    $toggleButton.setAttribute('aria-expanded', 'false');
    $toggleButton.textContent = `Choose ${this.fieldLabel}s`;
    $toggleButton.classList.add('govuk-button', 'govuk-button--secondary', this.toggleButtonClass);
    // visually hidden text
    const $visuallyHiddenButtonContent = document.createElement('span');
    $visuallyHiddenButtonContent.classList.add('govuk-visually-hidden');
    $visuallyHiddenButtonContent.textContent = this.legendText.toLowerCase().replace(`${this.fieldLabel}s`,'');
    // Create container for show / hide icon
    const $toggleButtonChevron = document.createElement('span');
    $toggleButtonChevron.classList.add(this.toggleButtonChevronClass);
    $toggleButton.append($visuallyHiddenButtonContent);
    $toggleButton.prepend($toggleButtonChevron);

    this.$fieldset.before($toggleButton);
  }

  handleToggleButtonClick() {
    let $button = this.$module.querySelector(`.${this.toggleButtonClass}`);
    $button.addEventListener("click", () => {
      let expanded = $button.getAttribute('aria-expanded') === 'true' || false;

      $button.setAttribute('aria-expanded', !expanded);
      $button.querySelector(`.${this.toggleButtonChevronClass}`).classList.toggle(this.toggleButtonChevronActiveClass);
      this.$fieldset.hidden = expanded;
    });

  }

  handleCheckboxClick() {
    this.$checkboxesArray.forEach(checkbox => {
      checkbox.addEventListener("click", () => {
        this.updateSelectionSummary(this.getSelectionCount());
      });
    });
  }

  getSelectionCount() {
    return Array.from(this.$checkboxesArray).filter((checkbox) => checkbox.checked).length;
  }

  initSelectionSummary() {
    const $hint = this.$module.querySelector('.govuk-hint');
    const $summaryText = document.createElement('p');
    $summaryText.classList.add('selection-summary__text');

    if (this.fieldLabel === 'folder') {
      $summaryText.classList.add('selection-summary__text--folders');
    }

    this.$selectionSummaryContainer.setAttribute('id', $hint.getAttribute('id'));
    this.$selectionSummaryContainer.append($summaryText);
    this.$fieldset.before(this.$selectionSummaryContainer);
    $hint.remove();

    this.updateSelectionSummary(this.getSelectionCount());
  }

  updateSelectionSummary(count) {
    const $selectionSummaryTextContainer =  this.$selectionSummaryContainer.querySelector('.selection-summary__text');
    let template;

    if (count === this.total) {
      template = 'all';
    } else if (count > 0) {
      template = 'some';
    } else {
      template = 'none';
    }

    $selectionSummaryTextContainer.textContent = this.selectionSummaryContent[template](count, this.total, this.fieldLabel);
  }

  addHeadingHideLegend() {
    const headingLevel = this.$module.getAttribute('data-heading-level') || '2';
    const $heading = document.createElement(`H${headingLevel}`);
    const $legend = this.$fieldset.querySelector('legend');
    $heading.classList.add('heading-small');
    $heading.textContent = `${this.legendText}`;
    this.$fieldset.before($heading);
    $legend.classList.add('govuk-visually-hidden');
  }
}

export default CollapsibleCheckboxes;
