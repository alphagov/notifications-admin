import { isSupported } from 'govuk-frontend';

class _ListEntry {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    const idPattern = $module.getAttribute('id');

    if (idPattern === null) { return false; }
    this.idPattern = idPattern;
    this.elementSelector = '.list-entry, .input-list__button--remove, .input-list__button--add';
    this.sharedInputClasses = ['govuk-input', 'govuk-input--numbered'];
    this.entries = [];
    this.$wrapper = $module;
    this.minEntries = 2;
    this.listItemName = this.$wrapper.dataset.listItemName;
    this.getCustomClasses();
    this.getSharedAttributes();

    this.getValuesAndErrors();
    this.maxEntries = this.entries.length;
    this.trimEntries();
    this.render();
    this.bindEvents();
  }

  entryTemplate (dataObj) {
    const { error, id, name, listItemName, number, value, customClasses, button, sharedInputClasses, sharedAttributes } = dataObj;

    return `
      <div class="list-entry">
        <div class="govuk-form-group${error ? ' govuk-form-group--error' : ''}">
          <label for="${id}" class="govuk-label govuk-input--numbered__label${error ? ' govuk-input--numbered__label--error' : ''}">
           <span class="govuk-visually-hidden">${listItemName} number </span>${number}.
          </label>
          ${error ?
          `<p id="${id}-error" class="govuk-error-message" data-notify-module="track-error" data-error-type="${error}" data-error-label="${name}">
           <span class="govuk-visually-hidden">Error: </span>${error}
          </p>` : ''}
          <input
           name="${name}"
           id="${id}"
           ${value ? `value="${value}"` : ''}
           class="${sharedInputClasses}${customClasses ? ` ${customClasses}` : ''}${error ? ' govuk-input--error' : ''}"
           ${error ? `aria-describedby="${id}-error"` : ''}
           ${sharedAttributes}
          />
          ${button ? `
          <button type="button" class="govuk-button govuk-button--secondary input-list__button--remove">
          Remove<span class="govuk-visually-hidden"> ${listItemName} number ${number}</span>
          </button>` : ''}
        </div>
      </div>`;
  }

  addButtonTemplate (dataObj) {
    const { listItemName, entriesLeft } = dataObj;

    return `<button type="button" class="govuk-button govuk-button--secondary input-list__button--add">Add another ${listItemName} (${entriesLeft} remaining)</button>`;
  }

  getSharedAttributes () {
    var $inputs = this.$wrapper.querySelectorAll('input'),
        attributeTemplate = dataObj => {
          const { name, value } = dataObj;

          return ` ${name}="${value}"`;
        },
        protectedAttributes = ['id', 'name', 'value', 'class', 'aria-describedby'],
        attributes = [],
        attrIdx,
        elmAttributes,
        getAttributesHTML;

    getAttributesHTML = function (attrsByElm) {
      var attrStr = '',
          elmIdx = attrsByElm.length,
          existingAttributes = [],
          elmAttrs,
          attrIdx;

      while (elmIdx--) {
        elmAttrs = attrsByElm[elmIdx];
        attrIdx = elmAttrs.length;
        while (attrIdx--) {
          // prevent duplicates
          if (!existingAttributes.includes(elmAttrs[attrIdx].name)) {
            attrStr += attributeTemplate({ 'name': elmAttrs[attrIdx].name, 'value': elmAttrs[attrIdx].value });
            existingAttributes.push(elmAttrs[attrIdx].name);
          }
        }
      }
      return attrStr;
    };

    $inputs.forEach(function (elm) {
      attrIdx = elm.attributes.length;
      elmAttributes = [];
      while(attrIdx--) {
        if (!protectedAttributes.includes(elm.attributes[attrIdx].name)) {
          elmAttributes.push({
            'name': elm.attributes[attrIdx].name,
            'value': elm.attributes[attrIdx].value
          });
        }
      }
      if (elmAttributes.length) {
        attributes.push(elmAttributes);
      }
    });

    this.sharedAttributes = (attributes.length) ? getAttributesHTML(attributes) : '';
  }

  getCustomClasses () {
    this.customClasses = [];
    this.$wrapper.querySelectorAll('input').forEach(function ($elm) {
      var customClassesForElm = [];

      $elm.classList.forEach(token => {
        if (!this.sharedInputClasses.includes(token) && (token !== 'govuk-input--error')) {
          customClassesForElm.push(token);
        }
      });

      if (customClassesForElm.length > 0) {
        this.customClasses.push(customClassesForElm);
      }
    }.bind(this));
  }

  getValuesAndErrors () {
    this.entries = [];
    this.errors = [];
    this.$wrapper.querySelectorAll('input').forEach(function ($elm) {
      var val = $elm.value;
      var $error = $elm.previousElementSibling;

      $error = $error.matches('p.govuk-error-message') ? $error : null;

      this.entries.push(val);
      if ($error !== null) {
        this.errors.push($error.textContent.trim().replace('Error: ', ''));
      } else {
        this.errors.push(null);
      }
    }.bind(this));
  }

  trimEntries () {
    var entryIdx = this.entries.length,
        newEntries = [];

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
    var pattern = this.idPattern.replace("list-entry-", "");
    if ("undefined" === typeof num) {
      return pattern;
    } else {
      return pattern + "-" + num;
    }
  }

  bindEvents () {
    this.$wrapper.addEventListener('click', function (e) {
      if (e.target.matches('.input-list__button--remove')) {
        this.removeEntry($(e.target));
      }
      if (e.target.matches('.input-list__button--add')) {
        this.addEntry();
      }
    }.bind(this));
  }

  shiftFocus (opts) {
    var numberTargeted;

    if (opts.action === 'remove') {
      numberTargeted = (opts.entryNumberFocused > 1) ? opts.entryNumberFocused - 1 : 1;
    } else { // opts.action === 'add'
      numberTargeted = opts.entryNumberFocused + 1;
    }
    this.$wrapper.querySelectorAll('.list-entry')[numberTargeted - 1].querySelector('input').focus();
  }

  removeEntryFromEntriesAndErrors (entryNumber) {
    var entryIdx = entryNumber - 1;

    this.entries.splice(entryIdx, 1);
    this.errors.splice(entryIdx, 1);
  }

  addEntry ($removeButton) {
    var currentLastEntryNumber = this.entries.length;

    this.getValuesAndErrors();
    this.entries.push('');
    this.render();
    this.shiftFocus({ 'action' : 'add', 'entryNumberFocused' : currentLastEntryNumber });
  }

  removeEntry ($removeButton) {
    var entryNumber = parseInt($removeButton.find('span').text().match(/\d+/)[0], 10);

    this.getValuesAndErrors();
    this.removeEntryFromEntriesAndErrors(entryNumber);
    this.render();
    this.shiftFocus({ 'action' : 'remove', 'entryNumberFocused' : entryNumber });
  }

  render () {
    this.$wrapper.querySelectorAll(this.elementSelector).forEach(el => el.remove());
    this.entries.forEach(function (entry, idx) {
      var entryNumber = idx + 1,
          error = this.errors[idx],
          customClasses = this.customClasses[idx],
          dataObj = {
            'id' : this.getId(entryNumber),
            'number' : entryNumber,
            'index': idx,
            'name' : this.getId(entryNumber),
            'value' : entry,
            'listItemName' : this.listItemName,
            'sharedInputClasses': this.sharedInputClasses.join(' '),
            'sharedAttributes': this.sharedAttributes
          };

      if (entryNumber > 1) {
        dataObj.button = true;
      }
      if (error !== null) {
        dataObj.error = error;
      }
      if (customClasses !== null) {
        dataObj.customClasses = ' ' + customClasses.join(' ');
      }
      this.$wrapper.insertAdjacentHTML('beforeend', this.entryTemplate(dataObj));
    }.bind(this));
    if (this.entries.length < this.maxEntries) {
      this.$wrapper.insertAdjacentHTML('beforeend', this.addButtonTemplate({
        'listItemName' : this.listItemName,
        'entriesLeft' : (this.maxEntries - this.entries.length)
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
