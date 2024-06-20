(function (Modules) {
  'use strict';

  var lists = [],
      listEntry,
      ListEntry;

  ListEntry = function (elm) {
    var $elm = $(elm),
        idPattern = $elm.prop('id');

    if (!idPattern) { return false; }
    this.idPattern = idPattern;
    this.elementSelector = '.list-entry, .input-list__button--remove, .input-list__button--add';
    this.sharedInputClasses = ['govuk-input', 'govuk-input--numbered'];
    this.entries = [];
    this.$wrapper = $elm;
    this.minEntries = 2;
    this.listItemName = this.$wrapper.data('listItemName');
    this.getCustomClasses();
    this.getSharedAttributes();

    this.getValuesAndErrors();
    this.maxEntries = this.entries.length;
    this.trimEntries();
    this.render();
    this.bindEvents();
  };
  ListEntry.optionalAttributes = ['aria-describedby'];
  ListEntry.prototype.entryTemplate = Hogan.compile(
    '<div class="list-entry">' +
      '<div class="govuk-form-group{{#error}} govuk-form-group--error{{/error}}">' +
        '<label for="{{{id}}}" class="govuk-label govuk-input--numbered__label{{#error}} govuk-input--numbered__label--error{{/error}}">' +
          '<span class="govuk-visually-hidden">{{listItemName}} number </span>{{number}}.' +
        '</label>' +
        '{{#error}}' +
        '<p id="{{{id}}}-error" class="govuk-error-message" data-notify-module="track-error" data-error-type="{{{error}}}" data-error-label="{{{name}}}">' +
          '<span class="govuk-visually-hidden">Error: </span>{{{error}}}' +
        '</p>' +
        '{{/error}}' +
        '<input' +
        ' name="{{name}}"' +
        ' id="{{id}}"' +
        ' {{#value}}value="{{value}}{{/value}}"' +
        ' class="{{{sharedInputClasses}}}{{#customClasses}} {{{customClasses}}}{{/customClasses}}"' +
        ' {{#error}}aria-describedby="{{{id}}}-error"{{/error}}' +
        ' {{{sharedAttributes}}}' +
        '/>' +
        '{{#button}}' +
        '<button type="button" class="govuk-button govuk-button--secondary input-list__button--remove">' +
        'Remove<span class="govuk-visually-hidden"> {{listItemName}} number {{number}}</span>' +
        '</button>' +
        '{{/button}}' +
      '</div>' +
    '</div>'
  );
  ListEntry.prototype.addButtonTemplate = Hogan.compile(
    '<button type="button" class="govuk-button govuk-button--secondary input-list__button--add">Add another {{listItemName}} ({{entriesLeft}} remaining)</button>'
  );
  ListEntry.prototype.getSharedAttributes = function () {
    var $inputs = this.$wrapper.find('input'),
        attributeTemplate = Hogan.compile(' {{name}}="{{value}}"'),
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
          if ($.inArray(elmAttrs[attrIdx].name, existingAttributes) === -1) {
            attrStr += attributeTemplate.render({ 'name': elmAttrs[attrIdx].name, 'value': elmAttrs[attrIdx].value });
            existingAttributes.push(elmAttrs[attrIdx].name);
          }
        }
      }
      return attrStr;
    };

    $inputs.each(function (idx, elm) {
      attrIdx = elm.attributes.length;
      elmAttributes = [];
      while(attrIdx--) {
        if ($.inArray(elm.attributes[attrIdx].name, protectedAttributes) === -1) {
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
  };
  ListEntry.prototype.getCustomClasses = function () {
    this.customClasses = [];
    this.$wrapper.find('input').each(function (idx, elm) {
      var customClassesForElm = [];

      elm.classList.forEach(token => {
        if ($.inArray(token, this.sharedInputClasses) === -1) {
          customClassesForElm.push(token);
        }
      });

      if (customClassesForElm.length > 0) {
        this.customClasses.push(customClassesForElm);
      }
    }.bind(this));
  };
  ListEntry.prototype.getValuesAndErrors = function () {
    this.entries = [];
    this.errors = [];
    this.$wrapper.find('input').each(function (idx, elm) {
      var val = $(elm).val();
      var $error = $(elm).prev('p.govuk-error-message');

      this.entries.push(val);
      if ($error.length > 0) {
        this.errors.push($error.get(0).textContent.trim().replace('Error: ', ''));
      } else {
        this.errors.push(null);
      }
    }.bind(this));
  };
  ListEntry.prototype.trimEntries = function () {
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
  };
  ListEntry.prototype.getId = function (num) {
    var pattern = this.idPattern.replace("list-entry-", "");
    if ("undefined" === typeof num) {
      return pattern;
    } else {
      return pattern + "-" + num;
    }
  };
  ListEntry.prototype.bindEvents = function () {
    this.$wrapper.on('click', '.input-list__button--remove', function (e) {
      this.removeEntry($(e.target));
    }.bind(this));
    this.$wrapper.on('click', '.input-list__button--add', function (e) {
      this.addEntry();
    }.bind(this));
  };
  ListEntry.prototype.shiftFocus = function (opts) {
    var numberTargeted;

    if (opts.action === 'remove') {
      numberTargeted = (opts.entryNumberFocused > 1) ? opts.entryNumberFocused - 1 : 1;
    } else { // opts.action === 'add'
      numberTargeted = opts.entryNumberFocused + 1;
    }
    this.$wrapper.find('.list-entry').eq(numberTargeted - 1).find('input').focus();
  };
  ListEntry.prototype.removeEntryFromEntriesAndErrors = function (entryNumber) {
    var entryIdx = entryNumber - 1;

    this.entries.splice(entryIdx, 1);
    this.errors.splice(entryIdx, 1);
  };
  ListEntry.prototype.addEntry = function ($removeButton) {
    var currentLastEntryNumber = this.entries.length;

    this.getValuesAndErrors();
    this.entries.push('');
    this.render();
    this.shiftFocus({ 'action' : 'add', 'entryNumberFocused' : currentLastEntryNumber });
  };
  ListEntry.prototype.removeEntry = function ($removeButton) {
    var entryNumber = parseInt($removeButton.find('span').text().match(/\d+/)[0], 10);

    this.getValuesAndErrors();
    this.removeEntryFromEntriesAndErrors(entryNumber);
    this.render();
    this.shiftFocus({ 'action' : 'remove', 'entryNumberFocused' : entryNumber });
  };
  ListEntry.prototype.render = function () {
    this.$wrapper.find(this.elementSelector).remove();
    $.each(this.entries, function (idx, entry) {
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
      this.$wrapper.append(this.entryTemplate.render(dataObj));
    }.bind(this));
    if (this.entries.length < this.maxEntries) {
      this.$wrapper.append(this.addButtonTemplate.render({
        'listItemName' : this.listItemName,
        'entriesLeft' : (this.maxEntries - this.entries.length)
      }));
    }
  };

  Modules.ListEntry = function () {

    this.start = component => lists.push(new ListEntry($(component)));

  };

})(window.GOVUK.NotifyModules);
