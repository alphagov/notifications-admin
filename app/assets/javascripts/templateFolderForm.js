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
        addNewFolderName: this.$form.find('#add_new_folder_form'),
        moveToNewFolderName: this.$form.find('#move_to_new_folder_form'),
      };

      this.render();
    };

    this.countSelectedCheckboxes = function() {
      return this.$form.find('input[type=checkbox]:checked').length;
    };

    this.render = function() {
      let numSelected = this.countSelectedCheckboxes();

      // hide everything
      Object.values(this.states).forEach($el => $el.hide());

      this.states.nothingSelectedButtons.show();
    };

    this.nothingSelectedButtons = function() {
      return `
        <div id="nothing_selected">
          <button class="button-secondary" value="new_template">New template</button>
          <button class="button-secondary" value="new_folder">New folder</button>
        </div>
      `;
    };

    this.itemsSelectedButtons = function() {
      return `
        <div id="items_selected">
          <button class="button-secondary" value="move_to_folder">Move</button>
          <button class="button-secondary" value="add_to_new_folder">Add to a new folder</button>
        </div>
      `;
    };
  };

})(window.GOVUK.Modules);
