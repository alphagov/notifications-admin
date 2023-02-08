(function(Modules) {
  "use strict";

  Modules.LiveCheckboxControls = function() {
    this.start = function(form) {
      this.$form = $(form);

      this.$liveRegionCounter = this.$form.find('.selection-counter');

      this.thing = {
        singular: this.$form.data('thingSingular') || 'option',
        plural: this.$form.data('thingPlural') || 'options'
      };

      this.$liveRegionCounter.before(this.nothingSelectedHint);
      this.$liveRegionCounter.before(this.itemsSelectedHint);

      // all the diff states that we want to show or hide
      this.states = [
        {
          key: 'nothing-selected-hint',
          $el: this.$form.find('#nothing-selected'),
          cancellable: false
        },
        {
          key: 'items-selected-hint',
          $el: this.$form.find('#items-selected'),
          cancellable: false
        }
      ];

      // clear/select-all buttons only relevant if JS enabled, so
      this.states.filter(state => state.key === 'nothing-selected-hint').forEach(state => this.onNothingSelected(state));
      this.states.filter(state => state.key === 'items-selected-hint').forEach(state => this.onSomethingSelected(state));

      this._lastState = this.$form.data('prev-state');
      if (this._lastState === undefined) {
        this.showInitialState();
      } else {
        this.currentState = this._lastState;
        this.render();
      }

      this.$form.on('change', 'input[type=checkbox]', () => this.checkboxChanged());
    };

    // Default behaviour - show a 'Select all' link/button if no checkboxes are selected
    this.onNothingSelected = function(state) {
      let selector = 'button[value=select-all]';
      let $clear = this.makeButton('Select all', {
        'onclick': () => {

          // uncheck all templates and folders
          this.$form.find('input:checkbox').prop('checked', true);

          // move focus to the first checkbox
          this.$form.find('input:checkbox').eq(0).focus();
          this.showInitialState();
        },
        'nonvisualText': `${this.thing.plural}`
      });

      state.$el.find('.checkbox-list-selected-counter').append($clear);
    };

    // Default behaviour - show a 'Clear' link/button if any checkboxes are selected
    this.onSomethingSelected = function(state) {
      let selector = 'button[value=clear]';
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

    this.selectionStatus = {
      'default': () => {
        return `No ${this.thing.plural} selected`;
      },
      'selected': numSelected => {
        const getString = () => {
          if (numSelected === 0) {
            return '';
          } else if (numSelected === 1) {
            return `1 ${this.thing.singular}`;
          } else {
            return `${numSelected} ${this.thing.plural}`;
          }
        };

        const results = [];

        if (numSelected > 0) {
          results.push(getString());
        }
        return results.join(', ') + ' selected';
      },
      'update': numSelected => {
        let message = (numSelected > 0) ? this.selectionStatus.selected(numSelected) : this.selectionStatus.default;

        $('.checkbox-list-selected-counter__count').html(message);
        this.$liveRegionCounter.html(message);
      }
    };

    this.makeButton = function(text, opts) {
      let $btn = $('<a href=""></a>')
                    .html(text)
                    .addClass('govuk-link govuk-link--no-visited-state js-action')
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
      this.checkboxChanged();
    };

    this.stateChanged = function() {
      let changed = this.currentState !== this._lastState;

      this._lastState = this.currentState;
      return changed;
    };

    this.checkboxChanged = function() {
      let numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothing-selected-hint' && numSelected !== 0) {
        // user has just selected first item
        this.currentState = 'items-selected-hint';
      } else if (this.currentState === 'items-selected-hint' && numSelected === 0) {
        // user has just deselected last item
        this.currentState = 'nothing-selected-hint';
      }

      if (this.stateChanged()) {
        this.render();
      }

      this.selectionStatus.update(numSelected);
    };

    this.countSelectedCheckboxes = function() {
      return this.$form.find('input:checkbox:checked').length;
    };

    this.render = function() {
      // detach everything, unless they are the currentState
      this.states.forEach(
        state => (state.key === this.currentState ? this.$liveRegionCounter.before(state.$el) : state.$el.detach())
      );
    };

    this.nothingSelectedHint = $(`
      <div id="nothing-selected">
        <div class="checkbox-list-selected-counter">
          <span class="checkbox-list-selected-counter__count" aria-hidden="true"></span>
        </div>
      </div>
    `).get(0);

    this.itemsSelectedHint = $(`
      <div id="items-selected">
        <div class="checkbox-list-selected-counter">
          <span class="checkbox-list-selected-counter__count" aria-hidden="true"></span>
        </div>
      </div>
    `).get(0);
  };

})(window.GOVUK.NotifyModules);
