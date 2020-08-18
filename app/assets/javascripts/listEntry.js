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
    this.entries = [];
    this.$wrapper = $elm;
    this.minEntries = 2;
    this.listItemName = this.$wrapper.data('listItemName');
    this.getSharedAttributes();

    this.getValues();
    this.maxEntries = this.entries.length;
    this.trimEntries();
    this.render();
    this.bindEvents();
  };
  ListEntry.optionalAttributes = ['aria-describedby'];
  ListEntry.prototype.entryTemplate = Hogan.compile(
    '<div class="list-entry">' +
      '<label for="{{{id}}}" class="govuk-input--numbered__label">' +
        '<span class="govuk-visually-hidden">{{listItemName}} number </span>{{number}}.' +
      '</label>' +
      '<input' +
        ' name="{{name}}"' +
        ' id="{{id}}"' +
        ' {{#value}}value="{{value}}{{/value}}"' +
        ' {{{sharedAttributes}}}' +
      '/>' +
      '{{#button}}' +
        '<button type="button" class="govuk-button govuk-button--secondary input-list__button--remove">' +
          'Remove<span class="govuk-visually-hidden"> {{listItemName}} number {{number}}</span>' +
        '</button>' +
      '{{/button}}' +
    '</div>'
  );
  ListEntry.prototype.addButtonTemplate = Hogan.compile(
    '<button type="button" class="govuk-button govuk-button--secondary input-list__button--add">Add another {{listItemName}} ({{entriesLeft}} remaining)</button>'
  );
  ListEntry.prototype.getSharedAttributes = function () {
    var $inputs = this.$wrapper.find('input'),
        attributeTemplate = Hogan.compile(' {{name}}="{{value}}"'),
        generatedAttributes = ['id', 'name', 'value'],
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
        if ($.inArray(elm.attributes[attrIdx].name, generatedAttributes) === -1) {
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
  ListEntry.prototype.getValues = function () {
    this.entries = [];
    this.$wrapper.find('input').each(function (idx, elm) {
      var val = $(elm).val();

      this.entries.push(val);
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
  ListEntry.prototype.removeEntryFromEntries = function (entryNumber) {
    var idx,
        len,
        newEntries = [];

    for (idx = 0, len = this.entries.length; idx < len; idx++) {
      if ((entryNumber - 1) !== idx) {
        newEntries.push(this.entries[idx]);
      }
    }
    this.entries = newEntries;
  };
  ListEntry.prototype.addEntry = function ($removeButton) {
    var currentLastEntryNumber = this.entries.length;

    this.getValues();
    this.entries.push('');
    this.render();
    this.shiftFocus({ 'action' : 'add', 'entryNumberFocused' : currentLastEntryNumber });
  };
  ListEntry.prototype.removeEntry = function ($removeButton) {
    var entryNumber = parseInt($removeButton.find('span').text().match(/\d+/)[0], 10);

    this.getValues();
    this.removeEntryFromEntries(entryNumber);
    this.render();
    this.shiftFocus({ 'action' : 'remove', 'entryNumberFocused' : entryNumber });
  };
  ListEntry.prototype.render = function () {
    this.$wrapper.find(this.elementSelector).remove();
    $.each(this.entries, function (idx, entry) {
      var entryNumber = idx + 1,
          dataObj = {
            'id' : this.getId(entryNumber),
            'number' : entryNumber,
            'index': idx,
            'name' : this.getId(entryNumber),
            'value' : entry,
            'listItemName' : this.listItemName,
            'sharedAttributes': this.sharedAttributes
          };

      if (entryNumber > 1) {
        dataObj.button = true;
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

})(window.GOVUK.Modules);
