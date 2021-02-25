(function (global) {
  "use strict";

  const GOVUK = global.GOVUK;

  function Summary (module) {
    this.module = module;
    this.$el = module.$formGroup.find('.selection-summary').first();
    this.fieldLabel = module.fieldLabel;
    this.total = module.total;
    this.addContent();
    this.update(module.getSelection());
  }
  Summary.prototype.templates = {
    all: (selection, total, field) => `All ${field}s`,
    some: (selection, total, field) => `${selection} of ${total} ${field}s`,
    none: (selection, total, field) => ({
        "folder": "No folders (only templates outside a folder)",
        "team member": "No team members (only you)"
    }[field] || `No ${field}s`)
  };
  Summary.prototype.addContent = function() {
    const $hint = this.module.$formGroup.find('.govuk-hint');
    this.$text = $(`<p class="selection-summary__text" />`);

    if (this.fieldLabel === 'folder') { this.$text.addClass('selection-summary__text--folders'); }

    this.$el.attr('id', $hint.attr('id'));
    this.$el.append(this.$text);
    $hint.remove();
  };
  Summary.prototype.update = function(selection) {
    let template;

    if (selection === this.total) {
      template = 'all';
    } else if (selection > 0) {
      template = 'some';
    } else {
      template = 'none';
    }

    this.$text.html(this.templates[template](selection, this.total, this.fieldLabel));
  };
  Summary.prototype.bindEvents = function () {
    // take summary out of tab order when focus moves
    this.$el.on('blur', (e) => $(this).attr('tabindex', '-1'));
  };

  function Footer (module) {
    this.module = module;
    this.fieldLabel = module.fieldLabel;
    this.fieldsetId = module.$fieldset.attr('id');
    this.$el = this.getEl(this.module.expanded);
    this.module.$formGroup.append(this.$el);
  }
  Footer.prototype.buttonContent = {
    change: (fieldLabel) => `Choose ${fieldLabel}s`,
    done: (fieldLabel) => `Done<span class="govuk-visually-hidden"> choosing ${fieldLabel}s</span>`
  };
  Footer.prototype.getEl = function (expanded) {
    const buttonState = expanded ? 'done' : 'change';
    const buttonContent = this.buttonContent[buttonState](this.fieldLabel);
    const stickyClass = expanded ? ' js-stick-at-bottom-when-scrolling' : '';

    return $(`<div class="selection-footer${stickyClass}">
              <button
                class="govuk-button govuk-button--secondary selection-footer__button"
                aria-expanded="${expanded ? 'true' : 'false'}"
                aria-controls="${this.fieldsetId}">
              ${buttonContent}
              </button>
            </div>`);
  };
  Footer.prototype.update = function (expanded) {
    this.$el.remove();
    this.$el = this.getEl(expanded);

    this.module.$formGroup.append(this.$el);

    // make footer sticky if expanded, clear up from it being sticky if not
    GOVUK.stickAtBottomWhenScrolling.recalculate();
  };

  function CollapsibleCheckboxes () {}
  CollapsibleCheckboxes.prototype._focusTextElement = ($el) => {
    $el
      .attr('tabindex', '-1')
      .focus();
  };
  CollapsibleCheckboxes.prototype.start = function(component) {
    this.$component = $(component);
    this.$formGroup = this.$component.find('.govuk-form-group').first();
    this.$fieldset = this.$formGroup.find('fieldset').first();
    this.$checkboxes = this.$fieldset.find('input[type=checkbox]');
    this.fieldLabel = this.$component.data('fieldLabel');
    this.total = this.$checkboxes.length;
    this.legendText = this.$fieldset.find('legend').first().text().trim();
    this.expanded = false;

    this.addHeadingHideLegend();

    // generate summary and footer
    this.footer = new Footer(this);
    this.summary = new Summary(this);

    this.$fieldset.before(this.summary.$el);

    // add custom classes
    this.$formGroup.addClass('selection-wrapper');
    this.$fieldset.addClass('selection-content');

    // hide checkboxes
    this.$fieldset.hide();

    this.bindEvents();
  };
  CollapsibleCheckboxes.prototype.getSelection = function() { return this.$checkboxes.filter(':checked').length; };
  CollapsibleCheckboxes.prototype.addHeadingHideLegend = function() {
    const headingLevel = this.$component.data('heading-level') || '2';

    this.$heading = $(`<h${headingLevel} class="heading-small">${this.legendText}</h${headingLevel}>`);
    this.$fieldset.before(this.$heading);

    this.$fieldset.find('legend').addClass('govuk-visually-hidden');
  };
  CollapsibleCheckboxes.prototype.expand = function(e) {
    if (e !== undefined) { e.preventDefault(); }

    if (!this.expanded) {
      this.$fieldset.show();
      this.expanded = true;
      this.summary.update(this.getSelection());
      this.footer.update(this.expanded);
    }

    // shift focus whether expanded or not
    this._focusTextElement(this.$fieldset);
  };
  CollapsibleCheckboxes.prototype.collapse = function(e) {
    if (e !== undefined) { e.preventDefault(); }

    if (this.expanded) {
      this.$fieldset.hide();
      this.expanded = false;
      this.summary.update(this.getSelection());
      this.footer.update(this.expanded);
    }

    // shift focus whether expanded or not
    this._focusTextElement(this.summary.$text);
  };
  CollapsibleCheckboxes.prototype.handleClick = function(e) {
    if (this.expanded) {
      this.collapse(e);
    } else {
      this.expand(e);
    }
  };
  CollapsibleCheckboxes.prototype.handleSelection = function(e) {
    this.summary.update(this.getSelection(), this.total, this.fieldLabel);
  };
  CollapsibleCheckboxes.prototype.bindEvents = function() {
    const self = this;

    this.$formGroup.on('click', '.govuk-button', this.handleClick.bind(this));
    this.$checkboxes.on('click', this.handleSelection.bind(this));

    this.summary.bindEvents(this);
  };

  GOVUK.Modules.CollapsibleCheckboxes = CollapsibleCheckboxes;

}(window));
