(function(Modules) {
  "use strict";

  Modules.TemplateFolderForm = function() {

    this.start = function(templateFolderForm) {
      this.$form = $(templateFolderForm);

      // remove the hidden unknown button - if you've got JS enabled then the action you want to do is implied by
      // which field is visible.
      this.$form.find('button[value=unknown]').remove();

      this.$stickyBottom = this.$form.find('#sticky_template_forms');

      this.$stickyBottom.append(this.nothingSelectedButtons);
      this.$stickyBottom.append(this.itemsSelectedButtons);

      // all the diff states that we want to show or hide
      this.states = [
        {key: 'nothing-selected-buttons', $el: this.$form.find('#nothing_selected'), cancellable: false},
        {key: 'items-selected-buttons', $el: this.$form.find('#items_selected'), cancellable: false},
        {key: 'move-to-existing-folder', $el: this.$form.find('#move_to_folder_radios'), cancellable: true},
        {key: 'move-to-new-folder', $el: this.$form.find('#move_to_new_folder_form'), cancellable: true},
        {key: 'add-new-folder', $el: this.$form.find('#add_new_folder_form'), cancellable: true},
        {key: 'add-new-template', $el: this.$form.find('#add_new_template_form'), cancellable: true}
      ];

      // cancel/clear buttons only relevant if JS enabled, so
      this.states.filter(state => state.cancellable).forEach((x) => this.addCancelButton(x));
      this.states.filter(state => state.key === 'items-selected-buttons').forEach(x => this.addClearButton(x));

      // first off show the new template / new folder buttons
      this.currentState = this.$form.data('prev-state') || 'unknown';
      if (this.currentState === 'unknown') {
        this.selectActionButtons();
      } else {
        this.render();
      }

      this.$form.on('click', 'button.button-secondary', (event) => this.actionButtonClicked(event));
      this.$form.on('change', 'input[type=checkbox]', () => this.templateFolderCheckboxChanged());
    };

    this.addCancelButton = function(state) {
      let $cancel = this.makeButton('Cancel', () => {

        // clear existing data
        state.$el.find('input:radio').prop('checked', false);
        state.$el.find('input:text').val('');

        // go back to action buttons
        this.selectActionButtons();
      });

      state.$el.find('[type=submit]').after($cancel);
    };

    this.addClearButton = function(state) {

      let $clear = this.makeButton('Clear', () => {

        // uncheck all templates and folders
        this.$form.find('input:checkbox').prop('checked', false);

        // go back to action buttons
        this.selectActionButtons();
      });

      state.$el.find('.template-list-selected-counter').append($clear);
    };

    this.makeButton = (text, fn) => $('<a></a>')
      .html(text)
      .addClass('js-cancel')
      .attr('tabindex', '0')
      .on('click keydown', event => {
        // space, enter or no keyCode (must be mouse input)
        if ([13, 32, undefined].indexOf(event.keyCode) > -1) {
          event.preventDefault();
          fn();
        }
      });

    this.selectActionButtons = function () {
      // If we want to show one of the grey choose actions state, we can pretend we're in the choose actions state,
      // and then pretend a checkbox was clicked to work out whether to show zero or non-zero options.
      // This calls a render at the end
      this.currentState = 'nothing-selected-buttons';
      this.templateFolderCheckboxChanged();
    };

    this.actionButtonClicked = function(event) {
      event.preventDefault();
      this.currentState = $(event.currentTarget).val();

      this.render();
    };

    this.templateFolderCheckboxChanged = function() {
      let numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothing-selected-buttons' && numSelected !== 0) {
        // user has just selected first item
        this.currentState = 'items-selected-buttons';
      } else if (this.currentState === 'items-selected-buttons' && numSelected === 0) {
        // user has just deselected last item
        this.currentState = 'nothing-selected-buttons';
      }

      this.render();

      $('.template-list-selected-counter-count').html(numSelected);

    };

    this.countSelectedCheckboxes = function() {
      return this.$form.find('input:checkbox:checked').length;
    };

    this.render = function() {
      // detach everything, unless they are the currentState
      this.states.forEach(
        state => (state.key === this.currentState ? this.$stickyBottom.append(state.$el) : state.$el.detach())
      );

      // make sticky JS recalculate its cache of the element's position
      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }
    };

    this.nothingSelectedButtons = `
      <div id="nothing_selected">
        <button class="button-secondary" value="add-new-template">New template</button>
        <button class="button-secondary" value="add-new-folder">New folder</button>
        <div class="template-list-selected-counter">
          Nothing selected
        </div>
      </div>
    `;

    this.itemsSelectedButtons = `
      <div id="items_selected">
        <button class="button-secondary" value="move-to-existing-folder">Move</button>
        <button class="button-secondary" value="move-to-new-folder">Add to a new folder</button>
        <div class="template-list-selected-counter">
          <span class="template-list-selected-counter-count">1</span> selected
        </div>
      </div>
    `;
  };

})(window.GOVUK.Modules);
