beforeAll(() => {
  Hogan = require('hogan.js');

  require('../../app/assets/javascripts/listEntry.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe("List entry", () => {
  const domains = [
    'gov.uk',
    'dwp.gov.uk',
    'hmrc.gov.uk',
    'defra.gov.uk',
    'beis.gov.uk',
    'dcms.gov.uk',
    'dfe.gov.uk',
    'did.gov.uk',
    'dvla.gov.uk',
    'dvsa.gov.uk'
  ];
  let inputList;

  const triggerEvent = (el, evtType) => {
    const evt = new Event(evtType, {
      bubbles: true,
      cancelable: true
    });

    el.dispatchEvent(evt);
  };

  const setFieldValues = (num) => {
    const items = inputList.querySelectorAll('.list-entry input[type=text]');

    while (num--) {
      items[num].setAttribute('value', domains[num]);
    }
  };

  beforeEach(() => {

    // set up DOM
    let entries = () => {
      let result = '';

      for (let idx = 0; idx < 10; idx++) {
        result += `
            <div class="list-entry">
              <div class="govuk-form-group">
                <label for="domains-${idx + 1}" class="govuk-label govuk-input--numbered__label">
                  <span class="govuk-visually-hidden">domain number </span>${idx + 1}.
                </label>
                <input type="text" name="domains-${idx + 1}" id="domains-${idx + 1}" class="govuk-input govuk-input--numbered govuk-!-width-full" autocomplete="off">
              </div>
            </div>`;
      }

      return result;
    };

    document.body.innerHTML =
      `<fieldset class="govuk-form-group" aria-describedby="domains-hint">
        <legend class="govuk-fieldset__legend">
          Domain names
          </span>
        </legend>
        <span id="domains-hint" class="govuk-hint">
          For example cabinet-office.gov.uk
        </span>
        <div class="input-list" data-module="list-entry" data-list-item-name="domain" id="list-entry-domains">
          ${entries()} }
        </div>
      </fieldset>`;

    inputList = document.querySelector('.input-list');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe("On page load", () => {

    test("Should remove all the fields except the first 2 if no values are present", () => {

      // start module
      window.GOVUK.modules.start();

      expect(inputList.querySelectorAll('.list-entry').length).toEqual(2);

    });

    test("Should remove all the fields except those first 2, and leave the first field as is if it has a value", () => {

      let fields = inputList.querySelectorAll('.list-entry input[type=text]');

      // set value of first field
      fields[0].setAttribute('value', domains[0]);

      // start module
      window.GOVUK.modules.start();

      // re-select fields, based on updated DOM
      fields = inputList.querySelectorAll('.list-entry input[type=text]');

      expect(fields.length).toEqual(2);
      expect(fields[0].getAttribute('value')).toEqual(domains[0]);

    });

    test("Should remove all the fields except those first 2, and leave the second field as is if it has a value", () => {

      let fields = inputList.querySelectorAll('.list-entry input[type=text]');

      // set value of first field
      fields[1].setAttribute('value', domains[1]);

      // start module
      window.GOVUK.modules.start();

      // re-select fields, based on updated DOM
      fields = inputList.querySelectorAll('.list-entry input[type=text]');

      expect(fields.length).toEqual(2);
      expect(fields[1].getAttribute('value')).toEqual(domains[1]);

    });
    test("Should remove all the fields except those with values if we have 4 values", () => {

      const fourDomains = domains.slice(0, 4);
      let fields = inputList.querySelectorAll('.list-entry input[type=text]');

      // set values of first 4 fields
      fourDomains.forEach((domain, idx) => { fields[idx].setAttribute('value', domain) });

      // start module
      window.GOVUK.modules.start();

      // re-select fields, based on updated DOM
      fields = inputList.querySelectorAll('.list-entry input[type=text]');

      expect(fields.length).toEqual(4);
      fourDomains.forEach((domain, idx) => {

        expect(fields[idx].getAttribute('value')).toEqual(domain);

      });

    });
    test("Should add 'remove' buttons to all fields except the first", () => {

      // start module
      window.GOVUK.modules.start();

      inputList.querySelectorAll('.list-entry').forEach((listEntry, idx) => {

        if (idx === 0) {
          expect(listEntry.querySelector('.input-list__button--remove')).toBeNull();
        } else {
          expect(listEntry.querySelector('.input-list__button--remove')).not.toBeNull();
        }

      });

    });

    test("Should add an 'add feature' button to the bottom of the list", () => {

      // start module
      window.GOVUK.modules.start();

      const listItems = inputList.children;

      expect(listItems[listItems.length - 1]);

    });

    test("Should copy all unique attributes into the new fields", () => {
      name_value_pairs = [];

      inputList.querySelectorAll('.list-entry input[type=text]').forEach((field, idx) => {

        name_value_pairs.push({
          'name': field.getAttribute('name'),
          'value': field.getAttribute('value')
        });

      });

      // start module
      window.GOVUK.modules.start();

      // re-select fields, based on updated DOM
      fields = inputList.querySelectorAll('.list-entry input[type=text]').forEach((field, idx) => {

        expect(field.getAttribute('name')).toEqual(name_value_pairs[idx].name);
        expect(field.getAttribute('value')).toEqual(name_value_pairs[idx].value);

      });

    });

    test("Should copy all shared attributes into the new fields", () => {

      inputList.querySelectorAll('.list-entry input[type=text]').forEach((field, idx) => {

        field.setAttribute('aria-describedby', 'hint1');
        field.classList.add('top-level-domain');

      });

      // start module
      window.GOVUK.modules.start();

      // re-select fields, based on updated DOM
      fields = inputList.querySelectorAll('.list-entry input[type=text]');

      expect(fields[0].getAttribute('aria-describedby')).toEqual('hint1');
      expect(fields[0].classList.contains('top-level-domain')).toBe(true);
    });
  });

  describe("When the 'remove' button is clicked", () => {

    beforeEach(() => {
      setFieldValues(10);

      // start module
      window.GOVUK.modules.start();
    });

    test("Should remove the associated field", () => {

      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[0], 'click');

      // list started with 10 fields
      expect(inputList.querySelectorAll('.list-entry').length).toEqual(9);

    });

    test("Should leave the list with the right numbers", () => {

      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[0], 'click');

      const newNums = Array.from(
                        inputList.querySelectorAll('.govuk-input--numbered__label')
                      )
                      .map((itemNum, idx) => {
                        return parseInt(itemNum.lastChild.nodeValue, 10);
                      });

      expect(newNums).toEqual([1,2,3,4,5,6,7,8,9]);

    });

    test("Should leave the list with the right values if you remove the last one", () => {

      // the first list item doesn't have a 'remove' button so there are only 9 for 10 items
      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[8], 'click');

      // the items have their values set to the 10 domains
      const expectedValues = domains.slice(0, -1);
      const itemValues = Array.from(
                          inputList.querySelectorAll('.list-entry input[type=text]')
                         )
                         .map(item => item.getAttribute('value'));

      expect(itemValues).toEqual(expectedValues);

    });

    test("Should leave the list with the right values if you remove the second one", () => {

      // the first 'remove' button is attached to the second list item
      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[0], 'click');

      // the items have their values set to the 10 domains
      const expectedValues = domains.slice();
      const itemValues = Array.from(
                          inputList.querySelectorAll('.list-entry input[type=text]')
                         )
                         .map(item => item.getAttribute('value'));

      // remove second item
      expectedValues.splice(1, 1)

      expect(itemValues).toEqual(expectedValues);

    });

    test("Should add the 'add' button if the added question is the 10th field", () => {

      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[8], 'click');

      expect(inputList.querySelector('.input-list__button--add')).not.toBeNull();

    });
  });

  describe("When the 'add feature' button is clicked", () => {
    let addButton;

    test("Should add a new field", () => {

      // start module
      window.GOVUK.modules.start();

      triggerEvent(inputList.querySelector('.input-list__button--add'), 'click');

      // inputList defaults to 2 items
      expect(inputList.querySelectorAll('.list-entry').length).toEqual(3);

    });
    test("Should update the number of fields users are allowed to enter if one is removed", () => {

      // start module
      window.GOVUK.modules.start();

      triggerEvent(inputList.querySelectorAll('.input-list__button--remove')[0], 'click');

      expect(inputList.querySelector('.input-list__button--add').textContent.trim())
        .toEqual('Add another domain (9 remaining)');

    });
    test("Should update the number of fields users are allowed to enter if one is added", () => {

      // start module
      window.GOVUK.modules.start();

      triggerEvent(inputList.querySelector('.input-list__button--add'), 'click');

      expect(inputList.querySelector('.input-list__button--add').textContent.trim())
        .toEqual('Add another domain (7 remaining)');

    });
    test("Should remove the 'add' button if the added question is the 10th field", () => {

      setFieldValues(9);

      // start module
      window.GOVUK.modules.start();

      triggerEvent(inputList.querySelector('.input-list__button--add'), 'click');

      expect(inputList.querySelector('.input-list__button--add')).toBeNull();

    });
  });
});
