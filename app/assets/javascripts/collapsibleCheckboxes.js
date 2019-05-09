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

      const legendText = this.$fieldset.find('legend').text().trim();

      this.addHeadingHideLegend(legendText);
      this.addFooterAndDoneButton(legendText);

      // create summary from component pieces and match text to current selection
      this.summary.addContent(legendText, this.fieldLabel);
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
    this.addHeadingHideLegend = function(legendText) {
      const headingLevel = this.$formGroup.data('heading-level') || '2';

      this.$heading = $(`<h${headingLevel} class="heading-small">${legendText}</h${headingLevel}>`);
      this.$fieldset.before(this.$heading);

      this.$fieldset.find('legend').addClass('visuallyhidden');
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
      addContent: function(legendText, fieldLabel) {
        const $content = $(`<p>
                               <span class="selection-summary__text"></span>
                               <button class="button button-secondary">Change<span class="visuallyhidden"> ${legendText}</span></button>
                            </p>`);

        this.$text = $content.find('.selection-summary__text');
        this.$changeButton = $content.find('button');

        if (fieldLabel === 'folder') { this.$text.addClass('selection-summary__text--folders'); }

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
    this.addFooterAndDoneButton = function (legendText) {
      this.$footer = $(`<div class="selection-footer">
                          <button class="button button-secondary">
                            <span class="visuallyhidden">${legendText} are </span>
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
