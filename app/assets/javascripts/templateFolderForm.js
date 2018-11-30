(function(Modules) {
  "use strict";

  Modules.TemplateFolderForm = function() {

    this.start = function(templateFolderForm) {
      this.$form = $(templateFolderForm);

      this.$stickyBottom = this.$form.find('#sticky_template_forms');

      this.$stickyBottom.append(this.nothingSelectedButtons);
      this.$stickyBottom.append(this.itemsSelectedButtons);

      // all the diff states that we want to show or hide
      this.states = {
        nothingSelectedButtons: this.$form.find('#nothing_selected'),
        itemsSelectedButtons: this.$form.find('#items_selected'),

        moveToFolderRadios: this.$form.find('#move_to_folder_radios'),
        moveToNewFolderForm: this.$form.find('#move_to_new_folder_form'),

        addNewFolderForm: this.$form.find('#add_new_folder_form'),
        addNewTemplateForm: this.$form.find('#add_new_template_form'),

      };

      // cancel buttons only relevant if JS enabled, so
      this.addCancelButton(this.states.moveToFolderRadios);
      this.addCancelButton(this.states.moveToNewFolderForm);
      this.addCancelButton(this.states.addNewFolderForm);
      this.addCancelButton(this.states.addNewTemplateForm);

      // first off show the new template / new folder buttons
      this.currentState = 'nothingSelectedButtons';

      this.$form.on('click', 'button.button-secondary', (event) => this.actionButtonClicked(event));
      this.$form.on('change', 'input[type=checkbox]', () => this.templateFolderCheckboxChanged());

      this.render();
    };

    this.addCancelButton = function($el) {
      let $cancel =  $('<a></a>')
          .html('Cancel')
          .click((event) => {
            event.preventDefault();
            // clear existing data
            $el.find('input:radio').prop('checked', false);
            $el.find('input:text').val('');

            // gross hack - pretend we're in the choose actions state, then pretend a checkbox was clicked to work out
            // whether to show zero or non-zero options. This calls a render at the end
            this.currentState = 'nothingSelectedButtons';
            this.templateFolderCheckboxChanged();
          });

      $el.append($cancel);
    };

    this.actionButtonClicked = function(event) {
      event.preventDefault();
      this.currentState = $(event.currentTarget).val();

      this.render();
    };

    this.templateFolderCheckboxChanged = function() {
      let numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothingSelectedButtons' && numSelected !== 0) {
        // user has just selected first item
        this.currentState = 'itemsSelectedButtons';
      } else if (this.currentState === 'itemsSelectedButtons' && numSelected === 0) {
        // user has just deselected last item
        this.currentState = 'nothingSelectedButtons';
      }

      this.render();
    };

    this.countSelectedCheckboxes = function() {
      return this.$form.find('input:checkbox:checked').length;
    };

    this.render = function() {
      // detach everything, unless they are the currentState
      Object.entries(this.states).forEach(
        ([state, $el]) => (state === this.currentState ? this.$stickyBottom.append($el) : $el.detach())
      );
    };

    this.nothingSelectedButtons = `
      <div id="nothing_selected">
        <button class="button-secondary" value="addNewTemplateForm">New template</button>
        <button class="button-secondary" value="addNewFolderForm">New folder</button>
      </div>
    `;

    this.itemsSelectedButtons = `
      <div id="items_selected">
        <button class="button-secondary" value="moveToFolderRadios">Move</button>
        <button class="button-secondary" value="moveToNewFolderForm">Add to a new folder</button>
      </div>
    `;
  };

})(window.GOVUK.Modules);
