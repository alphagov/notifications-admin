const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/liveSearch.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Live search', () => {

  let searchLabelText;
  let searchTextbox;
  let liveRegion
  let list;

  function liveRegionResults (num) {
    if (num === 1) {
      return "1 result";
    } else if (num === 0) {
      return "no results";
    } else {
      return `${num} results`;
    }
  };

  describe("With a list of radios", () => {

    searchLabelText = "Search branding styles by name";

    beforeEach(() => {

      const departmentData = {
        name: 'departments',
        hideLegend: true,
        fields: [
          {
            'label': 'NHS',
            'id': 'nhs',
            'name': 'branding',
            'value': 'nhs'
          },
          {
            'label': 'Department for Work and Pensions',
            'id': 'dwp',
            'name': 'branding',
            'value': 'dwp'
          },
          {
            'label': 'Department for Education',
            'id': 'dfe',
            'name': 'branding',
            'value': 'dfe'
          },
          {
            'label': 'Home Office',
            'id': 'home-office',
            'name': 'branding',
            'value': 'home-office'
          }
        ]
      };

      // set up DOM
      document.body.innerHTML = `
        <div class="live-search js-header" data-module="live-search" data-targets=".govuk-radios__item">
          <div class="form-group">
            <label class="form-label" for="search">
                ${searchLabelText}
            </label>
            <input autocomplete="off" class="form-control form-control-1-1 " id="search" name="search" rows="8" type="search" value="">
            <div role="region" aria-live="polite" class="live-search__status govuk-visually-hidden"></div>
          </div>
        </div>
        <form method="post" autocomplete="off" novalidate>
        </form>`;

      searchTextbox = document.getElementById('search');
      liveRegion = document.querySelector('.live-search__status');
      list = document.querySelector('form');

      // getRadioGroup returns a DOM node so append once DOM is set up
      list.appendChild(helpers.getRadioGroup(departmentData));

    });

    describe("When the page loads", () => {

      test("If there is no search term, the results should be unchanged", () => {

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(false);

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'Department';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(2);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(2)}`);

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'Department for Work';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(1)}`);

      });

      test("If an item doesn't match the search term but is selected, it should still show in the results", () => {

        searchTextbox.value = 'Department for Work';

        // mark an item as selected
        checkedItem = list.querySelector('input[id=nhs]');
        checkedItem.checked = true;

        // start the module
        window.GOVUK.modules.start();

        expect(window.getComputedStyle(checkedItem).display).not.toEqual('none');

      });

    });

    describe("When the search text changes", () => {

      test("If there is no search term, the results should be unchanged", () => {

        searchTextbox.value = 'Department';

        // start the module
        window.GOVUK.modules.start();

        // simulate the input of new search text
        searchTextbox.value = '';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(listItemsShowing.length));

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'Department';

        // start the module
        window.GOVUK.modules.start();

        // simulate the input of new search text
        searchTextbox.value = 'Home';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(1));

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'Department';

        // start the module
        window.GOVUK.modules.start();

        // simulate the input of new search text
        searchTextbox.value = 'Department for';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.govuk-radios__item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(2);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(2));

      });

      test("If an item doesn't match the search term but is selected, it should still show in the results", () => {

        searchTextbox.value = 'Department';

        // mark an item as selected
        checkedItem = list.querySelector('input[id=nhs]');
        checkedItem.checked = true;

        // start the module
        window.GOVUK.modules.start();

        // simulate the input of new search text
        searchTextbox.value = 'Home Office';
        helpers.triggerEvent(searchTextbox, 'input');

        expect(window.getComputedStyle(checkedItem).display).not.toEqual('none');

      });

    });

  });

  describe("With a list of checkboxes", () => {

    searchLabelText = "Search branding styles by name";

    beforeEach(() => {

      const templatesAndFolders = [
        {
          "label": "Appointments",
          "type": "folder",
          "meta": "2 templates"
        },
        {
          "label": "New patient",
          "type": "template",
          "meta": "Email template"
        },
        {
          "label": "Prescriptions",
          "type": "folder",
          "meta": "1 template, 1 folder"
        },
        {
          "label": "New doctor",
          "type": "template",
          "meta": "Email template"
        }
      ];

      // set up DOM
      document.body.innerHTML = `
        <div class="live-search js-header" data-module="live-search" data-targets="#template-list .template-list-item">
          <div class="form-group">
            <label class="form-label" for="search">
                ${searchLabelText}
            </label>
            <input autocomplete="off" class="form-control form-control-1-1 " id="search" name="search" rows="8" type="search" value="">
            <div role="region" aria-live="polite" class="live-search__status govuk-visually=hidden"></div>
          </div>
        </div>
        <form method="post" autocomplete="off" novalidate>
          <nav id="template-list">
            ${helpers.templatesAndFoldersCheckboxes(templatesAndFolders)}
          </nav>
        </form>`;

      searchTextbox = document.getElementById('search');
      liveRegion = document.querySelector('.live-search__status');
      list = document.querySelector('form');

    });

    describe("When the page loads", () => {

      test("If there is no search term, the results should be unchanged", () => {

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(false);

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'New';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        // should match 'New patient' and 'New doctor'
        expect(listItemsShowing.length).toEqual(2);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(2)}`);

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'New patient';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(1)}`);

      });

      test("If an item doesn't match the search term but is selected, it should still show in the results", () => {

        searchTextbox.value = 'New patient';

        // mark 'Appointments' item as selected
        checkedItem = list.querySelector('input[id=templates-or-folder-0]');
        checkedItem.checked = true;

        // start the module
        window.GOVUK.modules.start();

        // should show despite not matching
        expect(window.getComputedStyle(checkedItem).display).not.toEqual('none');

      });

      test("If the items have a block of text to match against, only results that match it should show", () => {

        searchTextbox.value = 'Email template';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        // 2 items contain the "Email template" text
        // only the text containing the name of the item is matched against (ie 'New patient')
        expect(listItemsShowing.length).toEqual(0);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(0)}`);

      });

    });

    describe("When the search text changes", () => {

      test("If there is no search term, the results should be unchanged", () => {

        searchTextbox.value = 'Appointments';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = '';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(listItemsShowing.length));

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'Appointments';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Prescriptions';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(1));

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'Appointments';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'New doctor';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(1));

      });

      test("If an item doesn't match the search term but is selected, it should still show in the results", () => {

        searchTextbox.value = 'Appointments';

        // mark 'Appointments' item as selected
        checkedItem = list.querySelector('input[id=templates-or-folder-0]');
        checkedItem.checked = true;

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Prescriptions';
        helpers.triggerEvent(searchTextbox, 'input');

        // should show despite not matching
        expect(window.getComputedStyle(checkedItem).display).not.toEqual('none');

      });

      test("If the items have a block of text to match against, only results that match it should show", () => {

        searchTextbox.value = 'Appointments';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Email template';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.template-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        // 2 items contain the "Email template" text
        // only the text containing the name of the item is matched against (ie 'New patient')
        expect(listItemsShowing.length).toEqual(0);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(0));

      });

    });

  })

  describe("With a list of content items", () => {

    searchLabelText = "Search by name or email address";

    function getContentItems (users) {

      function getPermissionsHTML (permissions) {

        const PERMISSIONS = ["Send messages", "Add and edit templates", "Manage settings, team and usage", "API integration"];
        let permissionsHTML = '';

        PERMISSIONS.forEach(permission => {
          let can = permissions.includes(permission);

          permissionsHTML += `
            <li>
              <span class="tick-cross-${can ? "tick" : "cross"}">
                <span class="visually-hidden">${can ? "Can" : "Can't"}</span>
                  ${permission}
                </span>
            </li>`;

         });

         return `<ul>
            ${permissionsHTML}
          </ul>`;

      };

      let result = '';

      users.forEach(user => result += `
        <div class="user-list-item">
          <h3 title="${user.email}">
            <span class="hint">
              <span class="live-search-relevant">${user.label} (${user.email})</span> (invited)
            </span>
          </h3>
          <ul class="tick-cross-list govuk-grid-row">
            <div class="tick-cross-list-permissions govuk-grid-column-three-quarters">
              ${getPermissionsHTML(user.permissions)}
              <div class="tick-cross-list-hint">
                  Can see 15 folders
              </div>
            </div>
            <li class="tick-cross-list-edit-link">
              <a class="govuk-link govuk-link--no-visited-state" href="/services/6658542f-0cad-491f-bec8-ab8457700ead/cancel-invited-user/21d6d54f-51e2-44ba-b48f-545d678c4c64">Cancel invitation</a>
            </li>
          </ul>
        </div>`);

      return result;

    };

    beforeEach(() => {

      const users = [
        {
          "label": "Template editor",
          "email": "template-editor@nhs.uk",
          "permissions" : ["Add and edit templates"]
        },
        {
          "label": "Software Developer",
          "email": "software-developer@nhs.uk",
          "permissions" : ["Send messages", "Add and edit templates", "team and usage", "API integration"]
        },
        {
          "label": "Team member",
          "email": "team-member@nhs.uk",
          "permissions" : ["Send messages", "Add and edit templates"]
        },
        {
          "label": "Administrator",
          "email": "admin@nhs.uk",
          "permissions" : ["Send messages", "Add and edit templates", "Manage settings, team and usage", "API integration"]
        }
      ];

      // set up DOM
      document.body.innerHTML = `
        <div class="live-search js-header" data-module="live-search" data-targets=".user-list-item">
          <div class="form-group" data-module="">
            <label class="form-label" for="search">
                ${searchLabelText}
            </label>
            <input autocomplete="off" class="form-control form-control-1-1 " data-module="" id="search" name="search" rows="8" type="search" value="">
            <div role="region" aria-live="polite" class="live-search__status govuk-visually-hidden"></div>
          </div>
        </div>
        <form method="post" autocomplete="off" novalidate>
          ${getContentItems(users)}
        </form>`;

      searchTextbox = document.getElementById('search');
      liveRegion = document.querySelector('.live-search__status');
      list = document.querySelector('form');

    });

    describe("When the page loads", () => {

      test("If there is no search term, the results should be unchanged", () => {

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(false);

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'admin';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(1)}`);

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'Administrator (admin@nhs.uk)';

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(searchTextbox.hasAttribute('aria-label')).toBe(true);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(1)}`);

      });

      test("If the items have a block of text to match against, only results that match it should show", () => {

        searchTextbox.value = "Add and edit templates";

        // start the module
        window.GOVUK.modules.start();

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        // all items contain the "Add and edit templates" permission so would match if all text was matched against the search term
        // only the text containing the label and email address is matched against
        expect(listItemsShowing.length).toEqual(0);
        expect(searchTextbox.getAttribute('aria-label')).toEqual(`${searchLabelText}, ${liveRegionResults(0)}`);

      });

    });

    describe("When the search text changes", () => {

      test("If there is no search term, the results should be unchanged", () => {

        searchTextbox.value = 'Admin';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = '';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(listItems.length);

      });

      test("If there is a single word search term, only the results that match should show", () => {

        searchTextbox.value = 'Admin';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Administrator';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(1));

      });

      test("If there is a search term made of several words, only the results that match should show", () => {

        searchTextbox.value = 'Admin';

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Administrator (admin@nhs.uk)';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        expect(listItemsShowing.length).toEqual(1);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(1));

      });

      test("If the items have a block of text to match against, only results that match it should show", () => {

        searchTextbox.value = "Admin";

        // start the module
        window.GOVUK.modules.start();

        // simulate input of new search text
        searchTextbox.value = 'Add and edit templates';
        helpers.triggerEvent(searchTextbox, 'input');

        const listItems = list.querySelectorAll('.user-list-item');
        const listItemsShowing = Array.from(listItems).filter(item => window.getComputedStyle(item).display !== 'none');

        // all items contain the "Add and edit templates" permission so would match if all text was matched against the search term
        // only the text containing the label and email address is matched against
        expect(listItemsShowing.length).toEqual(0);
        expect(liveRegion.textContent.trim()).toEqual(liveRegionResults(0));

      });

    });

  });

});
