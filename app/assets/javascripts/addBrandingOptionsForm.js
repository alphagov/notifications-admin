(function(Modules) {
  "use strict";

  Modules.AddBrandingOptionsForm = function() {

    this.start = function(addBrandingOptionsForm) {
      this.$form = $(addBrandingOptionsForm);

      this.$liveRegionCounter = this.$form.find('.selection-counter');

      this.$liveRegionCounter.before(this.nothingSelectedHint);
      this.$liveRegionCounter.before(this.itemsSelectedHint);

      // all the diff states that we want to show or hide
      this.states = [
        {
          key: 'nothing-selected-hint',
          $el: this.$form.find('#nothing_selected'),
          cancellable: false
        },
        {
          key: 'items-selected-hint',
          $el: this.$form.find('#items_selected'),
          cancellable: false
        }
      ];

      // clear button only relevant if JS enabled, so
      this.states.filter(state => state.key === 'items-selected-hint').forEach(x => this.addClearButton(x));

      // first off show the new template / new folder buttons
      this._lastState = this.$form.data('prev-state');
      if (this._lastState === undefined) {
        this.showInitialState();
      } else {
        this.currentState = this._lastState;
        this.render();
      }

      this.$form.on('change', 'input[type=checkbox]', () => this.BrandingOptionCheckboxChanged());
    };

    this.addClearButton = function(state) {
      let selector = 'button[value=add-new-template]';
      let $clear = this.makeButton('Clear', {
        'onclick': () => {

          // uncheck all templates and folders
          this.$form.find('input:checkbox').prop('checked', false);

          // move focus to the first checkbox
          this.$form.find('input:checkbox').eq(0).focus();
          this.showInitialState();
        },
        'nonvisualText': "selection"
      });

      state.$el.find('.checkbox-list-selected-counter').append($clear);
    };

    this.makeButton = (text, opts) => {
      let $btn = $('<a href=""></a>')
                    .html(text)
                    .addClass('govuk-link govuk-link--no-visited-state js-cancel')
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

    this.showInitialState = function () {
      // Reset the form to initial state, where nothing is selected
      this.currentState = 'nothing-selected-hint';
      this.BrandingOptionCheckboxChanged();
    };

    // method that checks the state against the last one, used prior to render() to see if needed
    this.stateChanged = function() {
      let changed = this.currentState !== this._lastState;

      this._lastState = this.currentState;
      return changed;
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

        if (numSelected.options > 0) {
          results.push(getString('options'));
        }
        return results.join(', ') + ' selected';
      },
      'update': numSelected => {
        let message = (numSelected.options > 0) ? this.selectionStatus.selected(numSelected) : this.selectionStatus.default;

        $('.checkbox-list-selected-counter__count').html(message);
        this.$liveRegionCounter.html(message);
      }
    };

    this.BrandingOptionCheckboxChanged = function() {
      let numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothing-selected-hint' && numSelected.options !== 0) {
        // user has just selected first item
        this.currentState = 'items-selected-hint';
      } else if (this.currentState === 'items-selected-hint' && numSelected.options === 0) {
        // user has just deselected last item
        this.currentState = 'nothing-selected-hint';
      }

      if (this.stateChanged()) {
        this.render();
      }

      this.selectionStatus.update(numSelected);
    };

    this.countSelectedCheckboxes = function() {
      const allSelected = this.$form.find('input:checkbox:checked');
      const results = {
        'options': allSelected.length
      };
      return results;
    };

    this.render = function() {
      let mode = 'default';
      let currentStateObj = this.states.filter(state => { return (state.key === this.currentState); })[0];

      // detach everything, unless they are the currentState
      this.states.forEach(
        state => (state.key === this.currentState ? this.$liveRegionCounter.before(state.$el) : state.$el.detach())
      );
    };

    this.nothingSelectedHint = $(`
      <div id="nothing_selected">
        <div class="checkbox-list-selected-counter">
          <span class="checkbox-list-selected-counter__count" aria-hidden="true">
            ${this.selectionStatus.default}
          </span>
        </div>
      </div>
    `).get(0);

    this.itemsSelectedHint = $(`
      <div id="items_selected">
        <div class="checkbox-list-selected-counter">
          <span class="checkbox-list-selected-counter__count" aria-hidden="true">
            ${this.selectionStatus.selected(1)}
          </span>
        </div>
      </div>
    `).get(0);
  };

})(window.GOVUK.NotifyModules);
