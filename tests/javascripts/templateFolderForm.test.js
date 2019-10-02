const helpers = require('./support/helpers');

function setFixtures (hierarchy) {

  const foldersCheckboxesHTML = function (filter) {
    let count = 0;

    // use closure to give all calls access to count
    return function (nodes) {
      let result = '';

      nodes
        .filter(node => node.type === 'folder')
        .forEach(node => {
          result += `<li class="multiple-choice">
                      <input id="node-${count}" name="move_to" type="radio" value="node-${count}">
                      <label class="block-label" for="node-${count}">
                        ${node.label}
                      </label>
                      ${node.children ? foldersCheckboxesHTML(node.children) : ''}
                    </li>`;
          count++;
        });

      return `<ul>${result}</ul>`;
    };

  }();

  function controlsHTML () {

    return `<div id="sticky_template_forms">
              <button type="submit" name="operation" value="unknown" hidden=""></button>
              <div id="move_to_folder_radios">
                <div class="js-will-stick-at-bottom-when-scrolling">
                  <div class="form-group ">
                    <fieldset id="move_to">
                      <legend class="form-label">
                        Choose a folder
                      </legend>
                      <div class="radios-nested">
                        ${foldersCheckboxesHTML(hierarchy)}
                      </div>
                    </fieldset>
                  </div>
                </div>
                <div class="js-will-stick-at-bottom-when-scrolling">
                  <div class="page-footer">
                    <button type="submit" class="button" name="operation" value="move-to-existing-folder">Move</button>
                  </div>
                </div>
              </div>
              <div id="move_to_new_folder_form">
                <fieldset class="js-will-stick-at-bottom-when-scrolling">
                  <legend class="visuallyhidden">Add to new folder</legend>
                  <div class="form-group">
                    <label class="form-label" for="move_to_new_folder_name">
                      Folder name
                    </label>
                    <input class="form-control form-control-1-1 " id="move_to_new_folder_name" name="move_to_new_folder_name" rows="8" type="text" value="">
                  </div>
                  <div class="page-footer">
                    <button type="submit" class="button" name="operation" value="move-to-new-folder">Add to new folder</button>
                  </div>
                </fieldset>
              </div>
              <div id="add_new_folder_form">
                <fieldset class="js-will-stick-at-bottom-when-scrolling">
                  <legend class="visuallyhidden">Add new folder</legend>
                  <div class="form-group">
                    <label class="form-label" for="add_new_folder_name">
                      Folder name
                    </label>
                    <input class="form-control form-control-1-1 " id="add_new_folder_name" name="add_new_folder_name" rows="8" type="text" value="">
                  </div>
                  <div class="page-footer">
                    <button type="submit" class="button" name="operation" value="add-new-folder">Add new folder</button>
                  </div>
                </fieldset>
              </div>
              <div id="add_new_template_form">
                <div class="js-will-stick-at-bottom-when-scrolling">
                  <div class="form-group ">
                    <fieldset id="add_template_by_template_type">
                      <legend class="form-label">
                        New template
                      </legend>
                      <div class="multiple-choice">
                        <input id="add_template_by_template_type-0" name="add_template_by_template_type" type="radio" value="email">
                        <label class="block-label" for="add_template_by_template_type-0">
                          Email
                        </label>
                      </div>
                      <div class="multiple-choice">
                        <input id="add_template_by_template_type-1" name="add_template_by_template_type" type="radio" value="sms">
                        <label class="block-label" for="add_template_by_template_type-1">
                          Text message
                        </label>
                      </div>
                      <div class="multiple-choice">
                        <input id="add_template_by_template_type-2" name="add_template_by_template_type" type="radio" value="letter">
                        <label class="block-label" for="add_template_by_template_type-2">
                          Letter
                        </label>
                      </div>
                      <div class="multiple-choice">
                        <input id="add_template_by_template_type-3" name="add_template_by_template_type" type="radio" value="copy-existing">
                        <label class="block-label" for="add_template_by_template_type-3">
                          Copy an existing template
                        </label>
                      </div>
                    </fieldset>
                  </div>
                </div>
                <div class="js-will-stick-at-bottom-when-scrolling">
                  <div class="page-footer">
                    <button type="submit" class="button" name="operation" value="add-new-template">Continue</button>
                  </div>
                </div>
              </div>
              <div class="selection-counter visuallyhidden" role="status" aria-live="polite">
                Nothing selected
              </div>
            </div>`
  };

  document.body.innerHTML = `
    <form method="post" data-module="template-folder-form">
      ${helpers.templatesAndFoldersCheckboxes(hierarchy)}
      ${controlsHTML()}
    </form>`;

};

function resetStickyMocks () {

  GOVUK.stickAtBottomWhenScrolling.recalculate.mockClear();
  GOVUK.stickAtBottomWhenScrolling.setMode.mockClear();

};

beforeAll(() => {
  require('../../app/assets/javascripts/templateFolderForm.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('TemplateFolderForm', () => {

  const hierarchy = [
    {
      'label': 'Folder 1',
      'type': 'folder',
      'meta': '1 template, 1 folder',
      'children': [
        {
          'label': 'Template 3',
          'type': 'template',
          'meta': 'Email template'
        },
        {
          'label': 'Folder 2',
          'type': 'folder',
          'meta': 'Empty',
          'children': []
        }
      ]
    },
    {
      'label': 'Template 1',
      'type': 'Email template',
      'meta': 'Email template'
    },
    {
      'label': 'Template 2',
      'type': 'template',
      'meta': 'Email template'
    }
  ];

  let templateFolderForm;
  let formControls;
  let visibleCounter;
  let hiddenCounter;

  beforeAll(() => {

    // stub out calls to sticky JS
    GOVUK.stickAtBottomWhenScrolling = {
      setMode: jest.fn(),
      recalculate: jest.fn()
    };

  });

  afterAll(() => {

    GOVUK.stickAtBottomWhenScrolling = undefined;

  });

  beforeEach(() => {

    setFixtures(hierarchy);

    templateFolderForm = document.querySelector('form[data-module=template-folder-form]');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  function getTemplateFolderCheckboxes () {
    return templateFolderForm.querySelectorAll('input[type=checkbox]');
  };

  function getVisibleCounter () {
    return formControls.querySelector('.template-list-selected-counter__count');
  };

  function getHiddenCounter () {
    return formControls.querySelector('[role=status]');
  };

  describe("Before the page loads", () => {
  
    // We need parts of the module to be made sticky, but by the module code,
    // not the sticky JS code that operates on the HTML at page load.
    // Because of this, they will need to be marked with classes
    test("the HTML for the module should contain placeholder classes on each part that needs to be sticky", () => {

      expect(templateFolderForm.querySelectorAll('#move_to_folder_radios > .js-will-stick-at-bottom-when-scrolling').length).toEqual(2);
      expect(templateFolderForm.querySelector('#move_to_new_folder_form > .js-will-stick-at-bottom-when-scrolling')).not.toBeNull();
      expect(templateFolderForm.querySelector('#add_new_folder_form > .js-will-stick-at-bottom-when-scrolling')).not.toBeNull();
      expect(templateFolderForm.querySelectorAll('#add_new_template_form > .js-will-stick-at-bottom-when-scrolling').length).toEqual(2);

    });
  
  });

  describe("When the page loads", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      formControls = templateFolderForm.querySelector('#sticky_template_forms');
      visibleCounter = getVisibleCounter();

    });

    afterEach(() => resetStickyMocks());

    test("the default controls and the counter should be showing", () => {

      expect(document.querySelector('button[value=add-new-template]')).not.toBeNull();
      expect(document.querySelector('button[value=add-new-folder]')).not.toBeNull();
      expect(visibleCounter).not.toBeNull();

    });

    // Our counter needs to be wrapped in an ARIA live region so changes to its content are
    // communicated to assistive tech'.
    // ARIA live regions need to be in the HTML before JS loads.
    // Because of this, we have a counter, in a live region, in the page when it loads, and
    // a duplicate, visible, one in the HTML the module adds to the page.
    // We hide the one in the live region to avoid duplication of it's content.
    describe("Selection counter", () => {

      beforeEach(() => {

        hiddenCounter = getHiddenCounter();

      })

      test("the visible counter should be hidden from assistive tech", () => {

        expect(visibleCounter.getAttribute('aria-hidden')).toEqual("true");

      });

      test("the content of both visible and hidden counters should match", () => {

        expect(visibleCounter.textContent.trim()).toEqual(hiddenCounter.textContent.trim());

      });

    });

    test("should make the current controls sticky", () => {

      // the class the sticky JS hooks into should be present
      expect(formControls.querySelector('#nothing_selected .js-stick-at-bottom-when-scrolling')).not.toBeNull();

      // .recalculate should have been called so the sticky JS picks up the controls
      expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

      // mode should have been set to 'default' as the controls only have one part
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('default');

    });

  });

  describe("Clicking 'New template'", () => {

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      formControls = templateFolderForm.querySelector('#sticky_template_forms');

      // reset sticky JS mocks called when the module starts
      resetStickyMocks();

      helpers.triggerEvent(formControls.querySelector('[value=add-new-template]'), 'click');

    });

    afterEach(() => resetStickyMocks());

    test("should show options for all the types of template", () => {

      const options = [
        'Email', 'Text message', 'Letter', 'Copy an existing template'
      ];

      const labels = Array.from(formControls.querySelectorAll('label'));
      const radios = Array.from(formControls.querySelectorAll('input[type=radio]'));

      options.forEach(option => {
        let matchingLabels = labels.filter(label => label.textContent.trim() === option);

        expect(matchingLabels.length > 0).toBe(true);

        let matchingRadio = formControls.querySelector(`#${matchingLabels[0].getAttribute('for')}`)

        expect(matchingRadio).not.toBeNull();
      });

    });

    test("should show a 'Cancel' link", () => {

      const cancelLink = formControls.querySelector('.js-cancel');

      expect(cancelLink).not.toBeNull();

    });

    test("should focus the fieldset", () => {

      expect(document.activeElement).toBe(formControls.querySelector('fieldset'));

    });

    test("should make the current controls sticky", () => {

      // the classes the sticky JS hooks into should be present for both parts
      expect(formControls.querySelectorAll('#add_new_template_form .js-stick-at-bottom-when-scrolling').length).toEqual(2);

      // .recalculate should have been called so the sticky JS picks up the controls
      expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

      // the mode should be set to 'dialog' so both parts can be sticky
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('dialog');

    });

    describe("When the 'Cancel' link is clicked after choosing to add a new template", () => {

      let addNewTemplateButton;

      beforeEach(() => {

        // reset sticky JS mocks called when the new template state loaded
        resetStickyMocks();

        helpers.triggerEvent(formControls.querySelector('.js-cancel'), 'click');

        addNewTemplateButton = formControls.querySelector('[value=add-new-template]');

      });

      test("the controls should reset", () => {

        expect(addNewTemplateButton).not.toBeNull();

      });

      test("the add new template control should be focused", () => {

        expect(document.activeElement).toBe(addNewTemplateButton);

      });

    });

  });

  describe("Clicking 'New folder'", () => {

    let textbox;

    afterEach(() => resetStickyMocks());

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      formControls = templateFolderForm.querySelector('#sticky_template_forms');

      // reset sticky JS mocks called when the module starts
      resetStickyMocks();

      helpers.triggerEvent(formControls.querySelector('[value=add-new-folder]'), 'click');

      textbox = formControls.querySelector('input[type=text]');

    });

    test("should show a textbox for the folder name", () => {

      expect(textbox).not.toBeNull();

      // check textbox has a label
      expect(formControls.querySelector(`label[for=${textbox.getAttribute('id')}]`)).not.toBeNull();

    });

    test("should focus the textbox", () => {

      expect(document.activeElement).toBe(textbox);

    });

    test("should make the current controls sticky", () => {

      // the class the sticky JS hooks into should be present
      expect(formControls.querySelector('#add_new_folder_form .js-stick-at-bottom-when-scrolling')).not.toBeNull();

      // .recalculate should have been called so the sticky JS picks up the controls
      expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

      // mode should have been set to 'default' as the controls only have one part
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('default');

    });

    describe("When the 'Cancel' link is clicked after choosing to add a new folder", () => {

      let addNewFolderButton;

      beforeEach(() => {

        helpers.triggerEvent(formControls.querySelector('.js-cancel'), 'click');

        addNewFolderButton = formControls.querySelector('button[value=add-new-folder]');

      });

      test("the controls should reset", () => {

        expect(addNewFolderButton).not.toBeNull();

      });

      test("the control for adding a new folder should be focused", () => {

        expect(document.activeElement).toBe(addNewFolderButton);

      });

    });

  });

  describe("When some templates/folders are selected", () => {

    let templateFolderCheckboxes;

    beforeEach(() => {

      // start module
      window.GOVUK.modules.start();

      templateFolderCheckboxes = getTemplateFolderCheckboxes();

      formControls = templateFolderForm.querySelector('#sticky_template_forms');

      // reset sticky JS mocks called when the module starts
      resetStickyMocks();

      helpers.triggerEvent(templateFolderCheckboxes[0], 'click');
      helpers.triggerEvent(templateFolderCheckboxes[2], 'click');

    });

    afterEach(() => resetStickyMocks());

    test("the buttons for moving to a new or existing folder are showing", () => {

      expect(formControls.querySelector('button[value=move-to-new-folder]')).not.toBeNull();
      expect(formControls.querySelector('button[value=move-to-existing-folder]')).not.toBeNull();

    });

    test("should make the current controls sticky", () => {

      // the class the sticky JS hooks into should be present
      expect(formControls.querySelector('#items_selected .js-stick-at-bottom-when-scrolling')).not.toBeNull();

      // .recalculate should have been called so the sticky JS picks up the controls
      expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

      // mode should have been set to 'default' as the controls only have one part
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
      expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('default');

    });

    describe("'Clear selection' link", () => {

      let clearLink;

      beforeEach(() => {

        clearLink = formControls.querySelector('.js-cancel');

      });

      test("the link has been added with the right text", () => {

        expect(clearLink).not.toBeNull();
        expect(clearLink.textContent.trim()).toEqual('Clear selection');

      });

      test("clicking the link clears the selection", () => {

        helpers.triggerEvent(clearLink, 'click');

        const checkedCheckboxes = Array.from(templateFolderCheckboxes).filter(checkbox => checkbox.checked);

        expect(checkedCheckboxes.length === 0).toBe(true);

      });

    });

    describe("Selection counter", () => {

      let visibleCounterText;
      let hiddenCounterText;

      beforeEach(() => {

        visibleCounterText = getVisibleCounter().textContent.trim();
        hiddenCounterText = getHiddenCounter().textContent.trim();

      });

      test("the content of both visible and hidden counters should match", () => {

        expect(visibleCounterText).toEqual(hiddenCounterText);

      });

      test("the content of the counter should reflect the selection", () => {
      
        expect(visibleCounterText).toEqual('2 selected');
      
      });
      
    });

    describe("Clicking the 'Move' button", () => {

      beforeEach(() => {

      // reset sticky JS mocks called when a selection was made
      resetStickyMocks();

        helpers.triggerEvent(formControls.querySelector('[value=move-to-existing-folder]'), 'click');

      });

      test("should show radios for all the folders in the hierarchy", () => {

        const foldersInHierarchy = [];

        function getFolders (nodes) {

          nodes.forEach(node => {
            if (node.type === 'folder') {

              foldersInHierarchy.push(node.label);
              if (node.children.length) { getFolders(node.children) }

            }
          });

        };

        getFolders(hierarchy);

        const folderLabels = Array.from(formControls.querySelectorAll('#move_to label'))
                                  .filter(label => label.textContent.trim() !== 'Templates');

        expect(folderLabels.map(label => label.textContent.trim())).toEqual(foldersInHierarchy);

        const radiosForLabels = folderLabels
                                  .map(label => formControls.querySelector(`#${label.getAttribute('for')}`))
                                  .filter(radio => radio !== null);

        expect(radiosForLabels.length).toEqual(foldersInHierarchy.length);

      });

      test("focus the 'Choose a folder' fieldset", () => {

        expect(document.activeElement).toBe(formControls.querySelector('#move_to'));

      });

      test("should make the current controls sticky", () => {

        // the classes the sticky JS hooks into should be present for both parts
        expect(formControls.querySelectorAll('#move_to_folder_radios .js-stick-at-bottom-when-scrolling').length).toEqual(2);

        // .recalculate should have been called so the sticky JS picks up the controls
        expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

        // the mode should be set to 'dialog' so both parts can be sticky
        expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
        expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('dialog');

      });

      describe("When the 'Cancel' link is clicked after choosing to move a template or folder", () => {

        let moveToFolderButton;

        beforeEach(() => {

          helpers.triggerEvent(formControls.querySelector('.js-cancel'), 'click');

          moveToFolderButton = formControls.querySelector('button[value=move-to-existing-folder]');

        });

        test("the controls should reset", () => {

          expect(moveToFolderButton).not.toBeNull();

        });

        test("the control for moving to an existing folder should be focused", () => {

          expect(document.activeElement).toBe(moveToFolderButton);

        });

      });

    });

    describe("Clicking the 'Add to new folder' button", () => {

      let textbox;

      beforeEach(() => {

        // reset sticky JS mocks called when a selection was made
        resetStickyMocks();

        helpers.triggerEvent(formControls.querySelector('[value=move-to-new-folder]'), 'click');

        textbox = formControls.querySelector('input[type=text]');

      });

      test("should show a textbox for the folder name", () => {

        expect(textbox).not.toBeNull();

        // check textbox has a label
        expect(formControls.querySelector(`label[for=${textbox.getAttribute('id')}]`)).not.toBeNull();

      });

      test("should focus the textbox", () => {

        expect(document.activeElement).toBe(textbox);

      });

      test("should make the current controls sticky", () => {

        // the class the sticky JS hooks into should be present
        expect(formControls.querySelector('#move_to_new_folder_form .js-stick-at-bottom-when-scrolling')).not.toBeNull();

        // .recalculate should have been called so the sticky JS picks up the controls
        expect(GOVUK.stickAtBottomWhenScrolling.recalculate.mock.calls.length).toEqual(1);

        // mode should have been set to 'default' as the controls only have one part
        expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls.length).toEqual(1);
        expect(GOVUK.stickAtBottomWhenScrolling.setMode.mock.calls[0][0]).toEqual('default');

      });

      describe("When the 'Cancel' link is clicked after choosing to add a template or folder to a new folder", () => {

        let moveToNewFolderButton;

        beforeEach(() => {

          helpers.triggerEvent(formControls.querySelector('.js-cancel'), 'click');

          moveToNewFolderButton = formControls.querySelector('button[value=move-to-new-folder]');

        });

        test("the controls should reset", () => {

          expect(moveToNewFolderButton).not.toBeNull();

        });

        test("the control for adding a new folder should be focused", () => {

          expect(document.activeElement).toBe(moveToNewFolderButton);

        });

      });

    });

  });

});
