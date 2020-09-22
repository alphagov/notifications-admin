(function(Modules) {
  "use strict";

  Modules.TemplateFolderForm = function() {

    this.start = function(templateFolderForm) {
      this.$form = $(templateFolderForm);

      // remove the hidden unknown button - if you've got JS enabled then the action you want to do is implied by
      // which field is visible.
      this.$form.find('button[value=unknown]').remove();

      this.$liveRegionCounter = this.$form.find('.selection-counter');

      this.$liveRegionCounter.before(this.nothingSelectedButtons);
      this.$liveRegionCounter.before(this.itemsSelectedButtons);

      // all the diff states that we want to show or hide
      this.states = [
        {
          key: 'nothing-selected-buttons',
          $el: this.$form.find('#nothing_selected'),
          cancellable: false
        },
        {
          key: 'items-selected-buttons',
          $el: this.$form.find('#items_selected'),
          cancellable: false
        },
        {
          key: 'move-to-existing-folder',
          $el: this.$form.find('#move_to_folder_radios'),
          cancellable: true,
          setFocus: () => $('#move_to_folder_radios').focus(),
          action: 'move to folder',
          description: 'Press move to confirm or cancel to close'
        },
        {
          key: 'move-to-new-folder',
          $el: this.$form.find('#move_to_new_folder_form'),
          cancellable: true,
          setFocus: () => $('#move_to_new_folder_form').focus(),
          action: 'move to new folder',
          description: 'Press add to new folder to confirm name or cancel to close'
        },
        {
          key: 'add-new-folder',
          $el: this.$form.find('#add_new_folder_form'),
          cancellable: true,
          setFocus: () => $('#add_new_folder_form').focus(),
          action: 'new folder',
          description: 'Press add new folder to confirm name or cancel to close'
        },
        {
          key: 'add-new-template',
          $el: this.$form.find('#add_new_template_form'),
          cancellable: true,
          setFocus: () => $('#add_new_template_form').focus(),
          action: 'new template',
          description: 'Press continue to confirm selection or cancel to close'
        }
      ];

      // cancel/clear buttons only relevant if JS enabled, so
      this.states.filter(state => state.cancellable).forEach((x) => this.addCancelButton(x));
      this.states.filter(state => state.key === 'items-selected-buttons').forEach(x => this.addClearButton(x));

      // make elements focusabled
      this.states.filter(state => state.setFocus).forEach(x => x.$el.attr('tabindex', '0'));

      this.addDescriptionsToStates();

      // activate stickiness of elements in each state
      this.activateStickyElements();

      // first off show the new template / new folder buttons
      this._lastState = this.$form.data('prev-state');
      if (this._lastState === undefined) {
        this.selectActionButtons();
      } else {
        this.currentState = this._lastState;
        this.render();
      }

      this.$form.on('click', 'button.govuk-button--secondary', (event) => this.actionButtonClicked(event));
      this.$form.on('change', 'input[type=checkbox]', () => this.templateFolderCheckboxChanged());
    };

    this.addDescriptionsToStates = function () {
      let id, description;

      $.each(this.states.filter(state => 'description' in state), (idx, state) => {
        id = `${state.key}__description`;
        description = `<p class="govuk-visually-hidden" id="${id}">${state.description}</p>`;
        state.$el
          .prepend(description)
          .attr('aria-describedby', id);
      });
    };

    this.activateStickyElements = function() {
      var oldClass = 'js-will-stick-at-bottom-when-scrolling';
      var newClass = 'js-stick-at-bottom-when-scrolling';

      this.states.forEach(state => {
        state.$el
          .find('.' + oldClass)
          .removeClass(oldClass)
          .addClass(newClass);
      });
    };

    this.addCancelButton = function(state) {
      let selector = `[value=${state.key}]`;
      let $cancel = this.makeButton('Cancel', {
        'onclick': () => {

          // clear existing data
          state.$el.find('input:radio').prop('checked', false);
          state.$el.find('input:text').val('');

          // go back to action buttons
          this.selectActionButtons(selector);
        },
        'cancelSelector': selector,
        'nonvisualText': state.action
      });

      state.$el.find('[type=submit]').after($cancel);
    };

    this.addClearButton = function(state) {
      let selector = 'button[value=add-new-template]';
      let $clear = this.makeButton('Clear', {
        'onclick': () => {

          // uncheck all templates and folders
          this.$form.find('input:checkbox').prop('checked', false);

          // go back to action buttons
          this.selectActionButtons(selector);
        },
        'nonvisualText': "selection"
      });

      state.$el.find('.template-list-selected-counter').append($clear);
    };

    this.makeButton = (text, opts) => {
      let $btn = $('<a href=""></a>')
                    .html(text)
                    .addClass('govuk-link govuk-link--no-visited-state js-cancel')
                    // isn't set if cancelSelector is undefined
                    .data('target', opts.cancelSelector || undefined)
                    .attr('tabindex', '0')
                    .on('click keydown', event => {
                      // space, enter or no keyCode (must be mouse input)
                      if ([13, 32, undefined].indexOf(event.keyCode) > -1) {
                        event.preventDefault();
                        if (opts.hasOwnProperty('onclick')) { opts.onclick(); }
                      }
                    });

        if (opts.hasOwnProperty('nonvisualText')) {
          $btn.append(`<span class="govuk-visually-hidden"> ${opts.nonvisualText}</span>`);
        }

        return $btn;
    };

    this.selectActionButtons = function (targetSelector) {
      // If we want to show one of the grey choose actions state, we can pretend we're in the choose actions state,
      // and then pretend a checkbox was clicked to work out whether to show zero or non-zero options.
      // This calls a render at the end
      this.currentState = 'nothing-selected-buttons';
      this.templateFolderCheckboxChanged();
      if (targetSelector) {
        $(targetSelector).focus();
      }
    };

    // method that checks the state against the last one, used prior to render() to see if needed
    this.stateChanged = function() {
      let changed = this.currentState !== this._lastState;

      this._lastState = this.currentState;
      return changed;
    };

    this.$singleNotificationChannel = (document.querySelector('div[id=add_new_template_form]')).getAttribute("data-channel");
    this.$singleChannelService = (document.querySelector('div[id=add_new_template_form]')).getAttribute("data-service");

    this.actionButtonClicked = function(event) {
      event.preventDefault();
      this.currentState = $(event.currentTarget).val();

      if (event.currentTarget.value === 'add-new-template' && this.$singleNotificationChannel) {
        window.location = "/services/" + this.$singleChannelService + "/templates/add-" + this.$singleNotificationChannel;
      } else {
        if (this.stateChanged()) {
          this.render();
        }
      }
    };

    this.selectionStatus = {
      'default': 'Nothing selected',
      'selected': numSelected => {
        const getString = key => {
          if (numSelected[key] === 0) {
            return '';
          } else if (numSelected[key] === 1) {
            return `1 ${key.substring(0, key.length - 1)}`;
          } else {
            return `${numSelected[key]} ${key}`;
          }
        };

        const results = [];

        if (numSelected.templates > 0) {
          results.push(getString('templates'));
        }
        if (numSelected.folders > 0) {
          results.push(getString('folders'));
        }
        return results.join(', ') + ' selected';
      },
      'update': numSelected => {
        let message = (numSelected.total > 0) ? this.selectionStatus.selected(numSelected) : this.selectionStatus.default;

        $('.template-list-selected-counter__count').html(message);
        this.$liveRegionCounter.html(message);
      }
    };

    this.templateFolderCheckboxChanged = function() {
      let numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothing-selected-buttons' && numSelected.total !== 0) {
        // user has just selected first item
        this.currentState = 'items-selected-buttons';
      } else if (this.currentState === 'items-selected-buttons' && numSelected.total === 0) {
        // user has just deselected last item
        this.currentState = 'nothing-selected-buttons';
      }

      if (this.stateChanged()) {
        this.render();
      }

      this.selectionStatus.update(numSelected);

      $('.template-list-selected-counter').toggle(this.hasCheckboxes());

    };

    this.hasCheckboxes = function() {
      return !!this.$form.find('input:checkbox').length;
    };

    this.countSelectedCheckboxes = function() {
      const allSelected = this.$form.find('input:checkbox:checked');
      const templates = allSelected.filter((idx, el) => $(el).siblings('.template-list-template').length > 0).length;
      const folders = allSelected.filter((idx, el) => $(el).siblings('.template-list-folder').length > 0).length;
      const results = {
        'templates': templates,
        'folders': folders,
        'total': allSelected.length
      };
      return results;
    };

    this.render = function() {
      let mode = 'default';
      let currentStateObj = this.states.filter(state => { return (state.key === this.currentState); })[0];
      let scrollTop;

      // detach everything, unless they are the currentState
      this.states.forEach(
        state => (state.key === this.currentState ? this.$liveRegionCounter.before(state.$el) : state.$el.detach())
      );

      // use dialog mode for states which contain more than one form control
      if (['move-to-existing-folder', 'add-new-template'].indexOf(this.currentState) !== -1) {
        mode = 'dialog';
      }
      GOVUK.stickAtBottomWhenScrolling.setMode(mode);
      // make sticky JS recalculate its cache of the element's position
      GOVUK.stickAtBottomWhenScrolling.recalculate();

      if (currentStateObj && ('setFocus' in currentStateObj)) {
        scrollTop = $(window).scrollTop();
        currentStateObj.setFocus();
        $(window).scrollTop(scrollTop);
      }
    };

    this.nothingSelectedButtons = $(`
      <div id="nothing_selected">
        <div class="js-stick-at-bottom-when-scrolling">
          <button class="govuk-button govuk-button--secondary govuk-!-margin-right-3 govuk-!-margin-bottom-1" value="add-new-template" aria-expanded="false">
            New template
          </button>
          <button class="govuk-button govuk-button--secondary govuk-!-margin-bottom-1" value="add-new-folder" aria-expanded="false">New folder</button>
          <div class="template-list-selected-counter">
            <span class="template-list-selected-counter__count" aria-hidden="true">
              ${this.selectionStatus.default}
            </span>
          </div>
        </div>
      </div>
    `).get(0);

    this.itemsSelectedButtons = $(`
      <div id="items_selected">
        <div class="js-stick-at-bottom-when-scrolling">
          <button class="govuk-button govuk-button--secondary govuk-!-margin-right-3 govuk-!-margin-bottom-1" value="move-to-existing-folder" aria-expanded="false">
            Move<span class="govuk-visually-hidden"> selection to folder</span>
          </button>
          <button class="govuk-button govuk-button--secondary govuk-!-margin-bottom-1" value="move-to-new-folder" aria-expanded="false">Add to new folder</button>
          <div class="template-list-selected-counter" aria-hidden="true">
            <span class="template-list-selected-counter__count" aria-hidden="true">
              ${this.selectionStatus.selected(1)}
            </span>
          </div>
        </div>
      </div>
    `).get(0);
  };

})(window.GOVUK.Modules);
