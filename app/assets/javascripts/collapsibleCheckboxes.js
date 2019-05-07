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
      this.summary.$el = this.$formGroup.find('.selection-summary');
      this.fieldLabel = this.$formGroup.data('fieldLabel');
      this.total = this.$checkboxes.length;

      this.addHeadingHideLegend();
      this.addFooterAndDoneButton();

      // create summary from component pieces and match text to current selection
      this.summary.addContent();
      this.summary.update(this.getSelection(), this.total, this.fieldLabel);
      this.$fieldset.before(this.summary.$el);

      // hide checkboxes
      this.$fieldset.hide();
      this.expanded = false;

      // set semantic relationships with aria attributes
      this.addARIAToButtons();

      this.bindEvents();
    };
    this.getSelection = function() { return this.$checkboxes.filter(':checked').length; };
    this.addHeadingHideLegend = function() {
      const headingLevel = this.$formGroup.data('heading-level') || '2';
      const $legend = this.$fieldset.find('legend');

      this.$heading = $(`<h${headingLevel} class="heading-small">${$legend.text().trim()}</h${headingLevel}>`);
      this.$fieldset.before(this.$heading);

      $legend.addClass('visuallyhidden');
    };
    this.summary = {
      templates: {
        all: (selection, total, field) => `All ${field}s`,
        some: (selection, total, field) => `${selection} of ${total} ${field}s`,
        none: (selection, total, field) => {
          if (field === 'folder') {
            return "No folders (only templates outside a folder)";
          } else {
            return `No ${field}s`;
          }
        }
      },
      addContent: function() {
        const $content = $(`<p>
                             <span class="selection-summary__text"></span> <button class="button button-secondary">Change</button>
                            </p>`);

        this.$text = $content.find('span');
        this.$changeButton = $content.find('button');

        this.$el.append($content);
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
    this.addFooterAndDoneButton = function () {
      this.$footer = $(`<div class="selection-footer">
                          <button class="button button-secondary">
                            Done
                          </button>
                        </div>`);

      this.$doneButton = this.$footer.find('.button');
      this.$fieldset.append(this.$footer);
    };
    this.addARIAToButtons = function () {
      const aria = {
        'aria-expanded': this.expanded,
        'aria-controls': this.$fieldset.attr('id')
      };

      this.summary.$changeButton.attr(aria);
      this.$doneButton.attr(aria);
    };
    this.expand = function(e) {
      if (e !== undefined) { e.preventDefault(); }

      if (!this.expanded) {
        this.$fieldset.show();
        this.summary.$changeButton.attr('aria-expanded', true);
        this.$doneButton.attr('aria-expanded', true);
        this.expanded = true;
      }

      // shift focus whether expanded or not
      _focusTextElement(this.$fieldset);
    };
    this.collapse = function(e) {
      if (e !== undefined) { e.preventDefault(); }

      if (this.expanded) {
        this.$fieldset.hide();
        this.summary.$changeButton.attr('aria-expanded', false);
        this.$doneButton.attr('aria-expanded', false);
        this.expanded = false;
      }

      // shift focus whether expanded or not
      _focusTextElement(this.summary.$text);
    };
    this.handleSelection = function(e) {
      this.summary.update(this.getSelection(), this.total, this.fieldLabel);
    };
    this.bindEvents = function() {
      const self = this;

      this.summary.$changeButton.on('click', this.expand.bind(this));
      this.$doneButton.on('click', this.collapse.bind(this));
      this.$checkboxes.on('click', this.handleSelection.bind(this));

      // take summary out of tab order when focus moves
      this.summary.$el.on('blur', (e) => $(this).attr('tabindex', '-1'));
    };
  };

}(window.GOVUK.Modules));
