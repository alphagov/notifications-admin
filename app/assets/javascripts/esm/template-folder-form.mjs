import { isSupported } from 'govuk-frontend';
import { stickAtBottomWhenScrolling } from './stick-to-window-when-scrolling.mjs';

class TemplateFolderForm {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$form = $module;

    this.setupSelectionStatus();
    this.setupDOM();
    this.setupStates();
    this.setupStateModifiers();
    this.setupInitialState();
    this.bindEvents();
  }

  setupDOM() {
    // remove the hidden unknown button - if you've got JS enabled then the action you want to do is implied by 
    // which field is visible.
    this.$form.querySelector('button[value=unknown]').remove();

    this.$liveRegionCounter = this.$form.querySelector('.selection-counter');

    this.nothingSelectedButtons = this.createNothingSelectedButtons();
    this.itemsSelectedButtons = this.createItemsSelectedButtons();

    this.$liveRegionCounter.before(this.nothingSelectedButtons);
    this.$liveRegionCounter.before(this.itemsSelectedButtons);
  }

  setupStates() {
    // all the diff states that we want to show or hide
    this.states = [
      {
        key: 'nothing-selected-buttons',
        $el: this.$form.querySelector('#nothing_selected'),
        cancellable: false
      },
      {
        key: 'items-selected-buttons',
        $el: this.$form.querySelector('#items_selected'),
        cancellable: false
      },
      {
        key: 'move-to-existing-folder',
        $el: this.$form.querySelector('#move_to_folder_radios'),
        cancellable: true,
        setFocus: () => document.getElementById('move_to_folder_radios').focus(),
        action: 'move to folder',
        description: 'Press move to confirm or cancel to close'
      },
      {
        key: 'move-to-new-folder',
        $el: this.$form.querySelector('#move_to_new_folder_form'),
        cancellable: true,
        setFocus: () => document.getElementById('move_to_new_folder_form').focus(),
        action: 'move to new folder',
        description: 'Press add to new folder to confirm name or cancel to close'
      },
      {
        key: 'add-new-folder',
        $el: this.$form.querySelector('#add_new_folder_form'),
        cancellable: true,
        setFocus: () => document.getElementById('add_new_folder_form').focus(),
        action: 'new folder',
        description: 'Press add new folder to confirm name or cancel to close'
      },
      {
        key: 'add-new-template',
        $el: this.$form.querySelector('#add_new_template_form'),
        cancellable: true,
        setFocus: () => document.getElementById('add_new_template_form').focus(),
        action: 'new template',
        description: 'Press continue to confirm selection or cancel to close'
      }
    ];
  }

  setupStateModifiers() {
    this.states.forEach(state => {
      if (!state.$el) return;
      // cancel/clear buttons only relevant if JS enabled
      if (state.cancellable) this.addCancelButton(state);
      if (state.key === 'items-selected-buttons') this.addClearButton(state);
      // make elements focusable
      if (state.setFocus) state.$el.setAttribute('tabindex', '0'); 
    });

    this.addDescriptionsToStates();

    // activate stickiness of elements in each state
    this.activateStickyElements();
  }

  setupInitialState() {
    // first off show the new template / new folder buttons
    this._lastState = this.$form.dataset.prevState;
    if (this._lastState === undefined) {
      this.selectActionButtons();
    } else {
      this.currentState = this._lastState;
      this.render();
    }
  }

  bindEvents() {
    this.$form.addEventListener('click', (event) => {
      if (event.target.closest('button.govuk-button--secondary')) {
        this.actionButtonClicked(event);
      }
    });

    this.$form.addEventListener('change', (event) => {
      if (event.target.matches('input[type="checkbox"]')) {
        this.templateFolderCheckboxChanged();
      }
    });
  }

  setupSelectionStatus() {
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

        document.querySelector('.checkbox-list-selected-counter__count').textContent = message;
        this.$liveRegionCounter.textContent = message;
      }
    };
  }

  addDescriptionsToStates() {
    this.states.forEach(state => {
      if (!state.$el || !state.description) return;

      const id = `${state.key}__description`;
      const $description = document.createElement('p');
      $description.className = 'govuk-visually-hidden';
      $description.id = id;
      $description.textContent = state.description;

      state.$el.prepend($description);
      state.$el.setAttribute('aria-describedby', id);
    });
  }

  activateStickyElements() {
    const oldClass = 'js-will-stick-at-bottom-when-scrolling';
    const newClass = 'js-stick-at-bottom-when-scrolling';

    this.states.forEach(state => {
      if (!state.$el) return;

      state.$el.querySelectorAll('.' + oldClass).forEach(el => {
        el.classList.remove(oldClass);
        el.classList.add(newClass);
      });
    });
  }

  addCancelButton(state) {
    let selector = `[value=${state.key}]`;
    let $cancel = this.makeButton('Cancel', {
      'onclick': () => {
        // clear existing data
        state.$el.querySelectorAll('input[type="radio"]').forEach(radio => radio.checked = false);
        state.$el.querySelectorAll('input[type="text"]').forEach(input => input.value = '');

        // go back to action buttons
        this.selectActionButtons(selector);
      },
      'cancelSelector': selector,
      'nonvisualText': state.action
    });

    state.$el.querySelector(selector).after($cancel);
  }

  addClearButton(state) {
    let selector = 'button[value=add-new-template]';
    let $clear = this.makeButton('Clear', {
      'onclick': () => {
        // uncheck all templates and folders
        this.$form.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);

        // go back to action buttons
        this.selectActionButtons(selector);
      },
      'nonvisualText': "selection"
    });

   state.$el.querySelector('.checkbox-list-selected-counter').append($clear);
  }

  makeButton(text, opts) {
    let $btn = document.createElement('a');
    $btn.setAttribute('href', '');
    $btn.innerHTML = text;
    $btn.classList.add('govuk-link', 'govuk-link--no-visited-state', 'js-cancel');
    // isn't set if cancelSelector is undefined
    if (opts.cancelSelector) {
      $btn.dataset.target = opts.cancelSelector;
    }
    $btn.setAttribute('tabindex', '0');

    const handleTrigger = (event) => {
      event.preventDefault();
      if (opts.hasOwnProperty('onclick')) { opts.onclick(); }
    };

    $btn.addEventListener('click', handleTrigger);
    $btn.addEventListener('keydown', (event) => {
      // enter or space pressed - https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key
      if (event.key === "Enter" || event.key === " ") {
        handleTrigger(event);
      }
    });

    if (opts.hasOwnProperty('nonvisualText')) {
      const span = document.createElement('span');
      span.className = 'govuk-visually-hidden';
      span.textContent = ` ${opts.nonvisualText}`; // space before it maintained
      $btn.append(span);
    }

    return $btn;
  }

  selectActionButtons(targetSelector) {
    // If we want to show one of the grey choose actions state, we can pretend we're in the choose actions state,
    // and then pretend a checkbox was clicked to work out whether to show zero or non-zero options.
    // This calls a render at the end
    this.currentState = 'nothing-selected-buttons';
    this.templateFolderCheckboxChanged();
    if (targetSelector) {
      this.$form.querySelector(targetSelector).focus();
    }
  }

  // method that checks the state against the last one, used prior to render() to see if needed
  stateChanged() {
    let changed = this.currentState !== this._lastState;

    this._lastState = this.currentState;
    return changed;
  }

  actionButtonClicked(event) {
    event.preventDefault();
    this.currentState = event.target.closest('button.govuk-button--secondary').value;

    if (this.stateChanged()) {
        this.render();
    }
  }

  templateFolderCheckboxChanged() {
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

    document.querySelector('.checkbox-list-selected-counter').style.display = this.hasCheckboxes() ? '' : 'none';
  }

  hasCheckboxes() {
    return !!this.$form.querySelectorAll('input[type="checkbox"]').length;
  }

  countSelectedCheckboxes() {
    const allSelected = this.$form.querySelectorAll('input[type="checkbox"]:checked');
  
    return Array.from(allSelected).reduce((acc, el) => {
      const parent = el.parentElement;
      if (parent) {
        if (parent.querySelector('.template-list-template')) acc.templates++;
        if (parent.querySelector('.template-list-folder')) acc.folders++;
      }
      acc.total++;
      return acc;
    }, { templates: 0, folders: 0, total: 0 });
  }

  render() {
    let mode = 'default';
    let currentStateObj = this.states.filter(state => { return (state.key === this.currentState); })[0];
    let scrollTop;

    // detach everything, unless they are the currentState
    this.states.forEach(
      state => (state.key === this.currentState ? (this.$liveRegionCounter && state.$el && this.$liveRegionCounter.before(state.$el)) : (state.$el && state.$el.remove()))
    );

    // use dialog mode for states which contain more than one form control
    if (['move-to-existing-folder', 'add-new-template'].indexOf(this.currentState) !== -1) {
      mode = 'dialog';
    }
    stickAtBottomWhenScrolling.setMode(mode);
    // make sticky JS recalculate its cache of the element's position
    stickAtBottomWhenScrolling.recalculate();

    if (currentStateObj && ('setFocus' in currentStateObj) && !this.formHasError()) {
      scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      currentStateObj.setFocus();
      window.scrollTo(window.pageXOffset || document.documentElement.scrollLeft, scrollTop);
    }
  }

  createNothingSelectedButtons() {
    const $container = document.createElement('div');
    $container.id = 'nothing_selected';

    const $stickyContainer = document.createElement('div');
    $stickyContainer.className = 'js-stick-at-bottom-when-scrolling';

    const $newTemplateBtn = document.createElement('button');
    $newTemplateBtn.type = 'button';
    $newTemplateBtn.className = 'govuk-button govuk-button--secondary govuk-!-margin-right-3 govuk-!-margin-bottom-1';
    $newTemplateBtn.value = 'add-new-template';
    $newTemplateBtn.textContent = 'New template';
    $newTemplateBtn.setAttribute('aria-expanded', 'false');

    const $newFolderBtn = document.createElement('button');
    $newFolderBtn.type = 'button';
    $newFolderBtn.className = 'govuk-button govuk-button--secondary govuk-!-margin-bottom-1';
    $newFolderBtn.value = 'add-new-folder';
    $newFolderBtn.setAttribute('aria-expanded', 'false');
    $newFolderBtn.textContent = 'New folder';

    const $counterDiv = document.createElement('div');
    $counterDiv.className = 'checkbox-list-selected-counter';

    const countSpan = document.createElement('span');
    countSpan.className = 'checkbox-list-selected-counter__count';
    countSpan.setAttribute('aria-hidden', 'true');
    countSpan.textContent = this.selectionStatus.default;

    $counterDiv.appendChild(countSpan);
    $stickyContainer.appendChild($newTemplateBtn);
    $stickyContainer.appendChild($newFolderBtn);
    $stickyContainer.appendChild($counterDiv);
    $container.appendChild($stickyContainer);

    return $container;
  }

  createItemsSelectedButtons() {
    const $container = document.createElement('div');
    $container.id = 'items_selected';

    const $stickyContainer = document.createElement('div');
    $stickyContainer.className = 'js-stick-at-bottom-when-scrolling';

    const $moveBtn = document.createElement('button');
    $moveBtn.type = 'button';
    $moveBtn.className = 'govuk-button govuk-button--secondary govuk-!-margin-right-3 govuk-!-margin-bottom-1';
    $moveBtn.value = 'move-to-existing-folder';
    $moveBtn.setAttribute('aria-expanded', 'false');
    $moveBtn.textContent = 'Move';

    const $srMessageContainer = document.createElement('span');
    $srMessageContainer.className = 'govuk-visually-hidden';
    $srMessageContainer.textContent = ' selection to folder';
    $moveBtn.appendChild($srMessageContainer);

    const $addFolderBtn = document.createElement('button');
    $addFolderBtn.type = 'button';
    $addFolderBtn.className = 'govuk-button govuk-button--secondary govuk-!-margin-bottom-1';
    $addFolderBtn.value = 'move-to-new-folder';
    $addFolderBtn.setAttribute('aria-expanded', 'false');
    $addFolderBtn.textContent = 'Add to new folder';

    const $counterDiv = document.createElement('div');
    $counterDiv.className = 'checkbox-list-selected-counter';
    $counterDiv.setAttribute('aria-hidden', 'true');

    const $countElement = document.createElement('span');
    $countElement.className = 'checkbox-list-selected-counter__count';
    $countElement.setAttribute('aria-hidden', 'true');
    $countElement.textContent = this.selectionStatus.selected(this.selectionStatus.default);

    $counterDiv.appendChild($countElement);
    $stickyContainer.appendChild($moveBtn);
    $stickyContainer.appendChild($addFolderBtn);
    $stickyContainer.appendChild($counterDiv);
    $container.appendChild($stickyContainer);

    return $container;
  }

  formHasError() {
    return Boolean(document.querySelector('.govuk-error-summary'));
  }
}

export default TemplateFolderForm;
