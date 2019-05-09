(function (Modules) {
  "use strict";

  Modules.CollapsibleCheckboxes = function() {
    const _focusTextElement = ($el) => {
      $el
        .attr('tabindex', '-1')
        .focus();
    };

    this.start = function(component) {
      this.$formGroup = $(component);
      this.$fieldset = this.$formGroup.find('fieldset');
      this.$checkboxes = this.$fieldset.find('input[type=checkbox]');
      this.fieldLabel = this.$formGroup.data('fieldLabel');
      this.total = this.$checkboxes.length;
      this.legendText = this.$fieldset.find('legend').text().trim();
      this.expanded = false;

      this.addHeadingHideLegend();

      // generate summary and footer
      this.summary.$el = this.$formGroup.find('.selection-summary');
      this.footer.$el = this.footer.getEl(this);
      this.footer.update(this);

      // create summary from component pieces and match text to current selection
      this.summary.addContent(this.legendText, this.fieldLabel);
      this.summary.update(this.getSelection(), this.total, this.fieldLabel);
      this.$fieldset.before(this.summary.$el);

      // add custom classes
      this.$formGroup.addClass('selection-wrapper');
      this.$fieldset.addClass('selection-content');

      // hide checkboxes
      this.$fieldset.hide();

      this.bindEvents();
    };
    this.getSelection = function() { return this.$checkboxes.filter(':checked').length; };
    this.addHeadingHideLegend = function() {
      const headingLevel = this.$formGroup.data('heading-level') || '2';

      this.$heading = $(`<h${headingLevel} class="heading-small">${this.legendText}</h${headingLevel}>`);
      this.$fieldset.before(this.$heading);

      this.$fieldset.find('legend').addClass('visuallyhidden');
    };
    this.summary = {
      templates: {
        all: (selection, total, field) => `All ${field}s`,
        some: (selection, total, field) => `${selection} of ${total} ${field}s`,
        none: (selection, total, field) => ({
            "folder": "No folders (only templates outside a folder)",
            "team member": "No team members (only you)"
        }[field] || `No ${field}s`)
      },
      addContent: function(legendText, fieldLabel) {
        this.$text = $(`<p class="selection-summary__text" />`);

        if (fieldLabel === 'folder') { this.$text.addClass('selection-summary__text--folders'); }

        this.$el.append(this.$text);
      },
      update: function(selection, total, field) {
        let template;

        if (selection === total) {
          template = 'all';
        } else if (selection > 0) {
          template = 'some';
        } else {
          template = 'none';
        }

        this.$text.html(this.templates[template](selection, total, field));
      }
    };
    this.footer = {
      buttonContent: {
        change: (fieldLabel) => `Choose ${fieldLabel}s`,
        done: (fieldLabel) => `Done<span class="visuallyhidden"> choosing ${fieldLabel}s</span>`
      },
      getEl: function (module) {
        const buttonState = module.expanded ? 'done' : 'change';
        const buttonContent = this.buttonContent[buttonState](module.fieldLabel);

        return $(`<div class="selection-footer">
                  <button
                    class="button button-secondary"
                    aria-expanded="${module.expanded ? 'true' : 'false'}"
                    aria-controls="${module.$fieldset.attr('id')}">
                  ${buttonContent}
                  </button>
                </div>`);
      },
      update: function (module) {
        this.$el.remove();
        this.$el = this.getEl(module);

        module.$formGroup.append(this.$el);
      }
    };
    this.expand = function(e) {
      if (e !== undefined) { e.preventDefault(); }

      if (!this.expanded) {
        this.$fieldset.show();
        this.expanded = true;
        this.footer.update(this);
      }

      // shift focus whether expanded or not
      _focusTextElement(this.$fieldset);
    };
    this.collapse = function(e) {
      if (e !== undefined) { e.preventDefault(); }

      if (this.expanded) {
        this.$fieldset.hide();
        this.expanded = false;
        this.footer.update(this);
      }

      // shift focus whether expanded or not
      _focusTextElement(this.summary.$text);
    };
    this.handleClick = function(e) {
      if (this.expanded) {
        this.collapse(e);
      } else {
        this.expand(e);
      }
    };
    this.handleSelection = function(e) {
      this.summary.update(this.getSelection(), this.total, this.fieldLabel);
    };
    this.bindEvents = function() {
      const self = this;

      this.$formGroup.on('click', '.button', this.handleClick.bind(this));
      this.$checkboxes.on('click', this.handleSelection.bind(this));

      // take summary out of tab order when focus moves
      this.summary.$el.on('blur', (e) => $(this).attr('tabindex', '-1'));
    };
  };

}(window.GOVUK.Modules));
