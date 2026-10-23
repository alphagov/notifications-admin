import { isSupported } from 'govuk-frontend';

// Event-handler attributes must never be cloned onto generated inputs.
const isUnsafeAttributeName = name => /^on/i.test(name);

class _ListEntry {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    const moduleId = $module.getAttribute('id');

    if (moduleId === null) { return false; }
    this.idPattern = moduleId.replace('list-entry-', '');
    this.elementSelector = '.list-entry, .input-list__button--remove, .input-list__button--add';
    this.sharedInputClasses = ['govuk-input', 'govuk-input--numbered'];
    this.entries = [];
    this.$wrapper = $module;
    this.minEntries = 2;
    this.listItemName = this.$wrapper.dataset.listItemName || '';
    this.getCustomClasses();
    this.getSharedAttributes();
    this.getValuesAndErrors();
    this.maxEntries = this.entries.length;
    this.trimEntries();
    this.render();
    this.bindEvents();
  }

  buildEntry (dataObj) {
    const {
      error, id, name, listItemName, number, value,
      customClasses, hasButton, sharedInputClasses, sharedAttributes
    } = dataObj;

    const $entry = document.createElement('div');
    $entry.className = 'list-entry';

    const $group = document.createElement('div');
    $group.className = 'govuk-form-group' + (error ? ' govuk-form-group--error' : '');

    // Label
    const $label = document.createElement('label');
    $label.htmlFor = id;
    $label.className = 'govuk-label govuk-input--numbered__label' +
      (error ? ' govuk-input--numbered__label--error' : '');

    const $labelHidden = document.createElement('span');
    $labelHidden.className = 'govuk-visually-hidden';
    $labelHidden.textContent = `${listItemName} number `;

    $label.append($labelHidden, `${number}.`);
    $group.append($label);

    // Error message
    if (error) {
      const $error = document.createElement('p');
      $error.id = `${id}-error`;
      $error.className = 'govuk-error-message';
      $error.setAttribute('data-notify-module', 'track-error');
      $error.setAttribute('data-error-type', error);
      $error.setAttribute('data-error-label', name);

      const $errorHidden = document.createElement('span');
      $errorHidden.className = 'govuk-visually-hidden';
      $errorHidden.textContent = 'Error: ';

      $error.append($errorHidden, error);
      $group.append($error);
    }

    // Input
    const $input = document.createElement('input');

    // Shared attributes first, so the explicit ones below always win.
    sharedAttributes.forEach(({ name: attrName, value: attrValue }) => {
      $input.setAttribute(attrName, attrValue);
    });

    $input.setAttribute('name', name);
    $input.setAttribute('id', id);
    if (value) {
      $input.setAttribute('value', value);
    }
    $input.className = [
      sharedInputClasses,
      customClasses.join(' '),
      error ? 'govuk-input--error' : ''
    ].filter(Boolean).join(' ');
    if (error) {
      $input.setAttribute('aria-describedby', `${id}-error`);
    }
    $group.append($input);

    // Remove button
    if (hasButton) {
      const $remove = document.createElement('button');
      $remove.type = 'button';
      $remove.className = 'govuk-button govuk-button--secondary input-list__button--remove';
      $remove.dataset.entryNumber = String(number);

      const $removeHidden = document.createElement('span');
      $removeHidden.className = 'govuk-visually-hidden';
      $removeHidden.textContent = ` ${listItemName} number ${number}`;

      $remove.append('Remove', $removeHidden);
      $group.append($remove);
    }

    $entry.append($group);
    return $entry;
  }

  buildAddButton (dataObj) {
    const { listItemName, entriesLeft } = dataObj;

    const $addBtn = document.createElement('button');
    $addBtn.type = 'button';
    $addBtn.className = 'govuk-button govuk-button--secondary input-list__button--add';
    $addBtn.textContent = `Add another ${listItemName} (${entriesLeft} remaining)`;
    return $addBtn;
  }

  // Returns an array of { name, value } pairs (not an HTML string).
  getSharedAttributes () {
    const protectedAttributes = ['id', 'name', 'value', 'class', 'aria-describedby'];
    const attributesByInput = [];

    this.$wrapper.querySelectorAll('input').forEach(function ($input) {
      const attrs = [];
      Array.from($input.attributes).forEach(attr => {
        if (!protectedAttributes.includes(attr.name) && !isUnsafeAttributeName(attr.name)) {
          attrs.push({ name: attr.name, value: attr.value });
        }
      });
      if (attrs.length) {
        attributesByInput.push(attrs);
      }
    });

    // Same precedence as before: later inputs / later attributes win,
    // duplicates by name are dropped.
    const seen = new Set();
    const shared = [];
    let inputIdx = attributesByInput.length;
    let attrIdx;

    while (inputIdx--) {
      attrIdx = attributesByInput[inputIdx].length;
      while (attrIdx--) {
        const attr = attributesByInput[inputIdx][attrIdx];
        if (!seen.has(attr.name)) {
          seen.add(attr.name);
          shared.push(attr);
        }
      }
    }

    this.sharedAttributes = shared;
  }

  getCustomClasses () {
    this.customClasses = [];
    this.$wrapper.querySelectorAll('input').forEach(function ($elm) {
      const customClassesForElm = [];

      $elm.classList.forEach(token => {
        if (!this.sharedInputClasses.includes(token) && (token !== 'govuk-input--error')) {
          customClassesForElm.push(token);
        }
      });

      this.customClasses.push(customClassesForElm);
    }.bind(this));
  }

  getValuesAndErrors () {
    this.entries = [];
    this.errors = [];
    this.$wrapper.querySelectorAll('input').forEach(function ($elm) {
      const val = $elm.value;
      let $error = $elm.previousElementSibling;

      $error = ($error && $error.matches('p.govuk-error-message')) ? $error : null;

      this.entries.push(val);
      if ($error !== null) {
        this.errors.push($error.textContent.trim().replace('Error: ', ''));
      } else {
        this.errors.push(null);
      }
    }.bind(this));
  }

  // Empty entries past the min amount to show don't need to be shown
  trimEntries () {
    let entryIdx = this.entries.length;
    const newEntries = [];

    while (entryIdx--) {
      if (this.entries[entryIdx] !== '') {
        newEntries.push(this.entries[entryIdx]);
      } else {
        if (entryIdx < this.minEntries) {
          newEntries.push('');
        }
      }
    }
    this.entries = newEntries.reverse();
  }

  getId (num) {
    if (typeof num === 'undefined') {
      return this.idPattern;
    } else {
      return `${this.idPattern}-${num}`;
    }
  }

  bindEvents () {
    this.$wrapper.addEventListener('click', function (e) {
      if (e.target.matches('.input-list__button--remove')) {
        this.removeEntry(e.target);
      }
      if (e.target.matches('.input-list__button--add')) {
        this.addEntry();
      }
    }.bind(this));
  }

  shiftFocus (opts) {
    let numberTargeted;

    if (opts.action === 'remove') {
      numberTargeted = (opts.entryNumberFocused > 1) ? opts.entryNumberFocused - 1 : 1;
    } else { // opts.action === 'add'
      numberTargeted = opts.entryNumberFocused + 1;
    }
    this.$wrapper.querySelectorAll('.list-entry')[numberTargeted - 1].querySelector('input').focus();
  }

  removeEntryFromEntriesAndErrors (entryNumber) {
    const entryIdx = entryNumber - 1;

    this.entries.splice(entryIdx, 1);
    this.errors.splice(entryIdx, 1);
  }

  addEntry () {
    const currentLastEntryNumber = this.entries.length;

    this.getValuesAndErrors();
    this.entries.push('');
    this.render();
    this.shiftFocus({ 'action': 'add', 'entryNumberFocused': currentLastEntryNumber });
  }

  removeEntry ($removeButton) {
    // Entry number is stored explicitly rather than scraped from label text,
    // so a list item name containing digits can't break it.
    const entryNumber = parseInt($removeButton.dataset.entryNumber, 10);

    this.getValuesAndErrors();
    this.removeEntryFromEntriesAndErrors(entryNumber);
    this.render();
    this.shiftFocus({ 'action': 'remove', 'entryNumberFocused': entryNumber });
  }

  render () {
    this.$wrapper.querySelectorAll(this.elementSelector).forEach(el => el.remove());

    this.entries.forEach(function (entry, idx) {
      const entryNumber = idx + 1;

      this.$wrapper.append(this.buildEntry({
        'id': this.getId(entryNumber),
        'number': entryNumber,
        'name': this.getId(entryNumber),
        'value': entry,
        'error': this.errors[idx] || null,
        'customClasses': this.customClasses[idx] || [],
        'hasButton': entryNumber > 1,
        'listItemName': this.listItemName,
        'sharedInputClasses': this.sharedInputClasses.join(' '),
        'sharedAttributes': this.sharedAttributes
      }));
    }.bind(this));

    if (this.entries.length < this.maxEntries) {
      this.$wrapper.append(this.buildAddButton({
        'listItemName': this.listItemName,
        'entriesLeft': (this.maxEntries - this.entries.length)
      }));
    }
  }
}

const _lists = [];

class ListEntry {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    _lists.push(new _ListEntry($module));
  }
}

export default ListEntry;
