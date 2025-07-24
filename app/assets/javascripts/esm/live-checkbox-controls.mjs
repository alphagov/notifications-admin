import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class LiveCheckboxControls {
    constructor (form) {
      if (!isSupported()) {
        return this;
      }
      this.$form = form;
      this.$liveRegionCounter = this.$form.querySelector('.selection-counter');

      // variants of the noun for checkbox items, used by sentences describing what is selected
      this.thing = {
        singular: this.$form.dataset.thingSingular || 'option',
        plural: this.$form.dataset.thingPlural || 'options'
      };

      this.$liveRegionCounter.insertAdjacentHTML('beforebegin', this.nothingSelectedHint);
      this.$liveRegionCounter.insertAdjacentHTML('beforebegin', this.itemsSelectedHint);

      // all the diff states that we want to show or hide
      this.states = [
        {
          key: 'nothing-selected-hint',
          $el: this.$form.querySelector('#nothing-selected'),
          cancellable: false
        },
        {
          key: 'items-selected-hint',
          $el: this.$form.querySelector('#items-selected'),
          cancellable: false
        }
      ];

      // clear/select-all buttons only relevant if JS enabled, so
      this.states.filter(state => state.key === 'nothing-selected-hint').forEach(state => this.onNothingSelected(state));
      this.states.filter(state => state.key === 'items-selected-hint').forEach(state => this.onSomethingSelected(state));

      this._lastState = this.$form.dataset.prevState;
      if (this._lastState === undefined) {
        this.showInitialState();
      } else {
        this.currentState = this._lastState;
        this.render();
      }

      this.$form.addEventListener('change', (evt) => {
        if (evt.target.matches('input[type=checkbox]')) { this.onCheckboxChanged(); }
      });
    }

    // Default behaviour - show a 'Select all' link/button if no checkboxes are selected
    onNothingSelected (state) {
      const $clear = this.makeActionButton('Select all', {
        'onclick': () => {

          // check all templates and folders
          this.$form.querySelectorAll('input[type=checkbox]').forEach(el => {
            el.setAttribute('checked', 'checked');
            el.checked = true;
          });

          // move focus to the first checkbox
          this.$form.querySelectorAll('input[type=checkbox]')[0].focus();
          this.showInitialState();
        },
        'nonvisualText': `${this.thing.plural}`
      });

      state.$el.querySelector('.checkbox-list-selected-counter').append($clear);
    }

    // Default behaviour - show a 'Clear' link/button if any checkboxes are selected
    onSomethingSelected (state) {
      const $clear = this.makeActionButton('Clear', {
        'onclick': () => {

          // uncheck all templates and folders
          this.$form.querySelectorAll('input[type=checkbox]').forEach(el => {
            el.removeAttribute('checked');
            el.checked = false;
          });

          // move focus to the first checkbox
          this.$form.querySelectorAll('input[type=checkbox]')[0].focus();
          this.showInitialState();
        },
        'nonvisualText': "selection"
      });

      state.$el.querySelector('.checkbox-list-selected-counter').append($clear);
    }

    get selectionStatus () {
      return {
        'default': () => {
          return `No ${this.thing.plural} selected`;
        },
        'selected': numSelected => {
          if (numSelected === 1) {
            return `1 ${this.thing.singular} selected`;
          } else {
            return `${numSelected} ${this.thing.plural} selected`;
          }
        },
        'update': numSelected => {
          const message = (numSelected > 0) ? this.selectionStatus.selected(numSelected) : this.selectionStatus.default();

          document.querySelector('.checkbox-list-selected-counter__count').innerHTML = message;
          this.$liveRegionCounter.innerHTML = message;
        }
      };
    }

    makeActionButton (text, opts) {
      const $btn = document.createElement('a');
      const callback = (evt) => {
        // space, enter or no keyCode (must be mouse input)
        if ([13, 32, undefined].includes(evt.keyCode)) {
          evt.preventDefault();
          if (opts.hasOwnProperty('onclick')) { opts.onclick(); }
        }
      };

      $btn.setAttribute('href', '');
      $btn.innerHTML = text;
      $btn.classList.add('govuk-link', 'govuk-link--no-visited-state', 'js-action');
      $btn.setAttribute('tabindex', '0');
      $btn.addEventListener('click', callback);
      $btn.addEventListener('keydown', callback);

      if (opts.hasOwnProperty('nonvisualText')) {
        $btn.insertAdjacentHTML('beforeend', `<span class="govuk-visually-hidden"> ${opts.nonvisualText}</span>`);
      }

      return $btn;
    }

    showInitialState () {
      // Reset the form to initial state, where nothing is selected
      this.currentState = 'nothing-selected-hint';
      this.onCheckboxChanged();
    }

    stateHasChanged () {
      const changed = this.currentState !== this._lastState;

      this._lastState = this.currentState;
      return changed;
    }

    onCheckboxChanged () {
      const numSelected = this.countSelectedCheckboxes();

      if (this.currentState === 'nothing-selected-hint' && numSelected !== 0) {
        // user has just selected first item
        this.currentState = 'items-selected-hint';
      } else if (this.currentState === 'items-selected-hint' && numSelected === 0) {
        // user has just deselected last item
        this.currentState = 'nothing-selected-hint';
      }

      if (this.stateHasChanged()) {
        this.render();
      }

      this.selectionStatus.update(numSelected);
    };

    countSelectedCheckboxes () {
      return this.$form.querySelectorAll('input[type=checkbox]:checked').length;
    }

    render () {
      // detach everything, unless they are the currentState
      this.states.forEach(
        state => (state.key === this.currentState ? this.$liveRegionCounter.insertAdjacentElement('beforebegin', state.$el) : state.$el.remove())
      );
    }

    get nothingSelectedHint () {
      return `
        <div id="nothing-selected">
          <div class="checkbox-list-selected-counter">
            <span class="checkbox-list-selected-counter__count" aria-hidden="true"></span>
          </div>
        </div>`;
    }

    get itemsSelectedHint () {
      return `
        <div id="items-selected">
          <div class="checkbox-list-selected-counter">
            <span class="checkbox-list-selected-counter__count" aria-hidden="true"></span>
          </div>
        </div>`;
  }
}

export default LiveCheckboxControls;
