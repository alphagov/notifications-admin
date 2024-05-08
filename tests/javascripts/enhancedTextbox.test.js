const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/enhancedTextbox.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Enhanced textbox', () => {

  let input;
  let textarea;
  let backgroundEl;
  let stylesheet;

  beforeAll(() => {

    // set some default styling
    stylesheet = document.createElement('style');

    stylesheet.innerHTML = ".govuk-textarea-highlight__textbox { padding: 2px; width: 576px; border-width: 1px; }";
    stylesheet.innerHTML += "textarea.govuk-textarea-highlight__textbox { height: 224px; }";

    document.getElementsByTagName('head')[0].appendChild(stylesheet);

  });

  afterAll(() => {

    stylesheet.parentNode.removeChild(stylesheet);

  });

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <div class="govuk-form-group govuk-textarea-highlight">
        <label class="govuk-label" for="template_content">Message</label>
        <textarea class="govuk-textarea govuk-!-width-full govuk-textarea-highlight__textbox" id="template_content" name="template_content" rows="8" data-notify-module="enhanced-textbox" data-highlight-placeholders="true"></textarea>
      </div>`;

    textarea = document.querySelector('textarea');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe("When the page loads", () => {

    test("An element should be added as a layer below the textbox to hold the highlights", () => {

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // both the textbox and the element behind need a wrapping element
      expect(textarea.parentNode.classList.contains('govuk-textarea-highlight__wrapper')).toBe(true);

      expect(backgroundEl).not.toBeNull();
      expect(backgroundEl.classList.contains('govuk-textarea-highlight__background')).toBe(true);

    });

    test("The element's dimensions and border-width should match those of the textbox", () => {

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      expect(backgroundEl.style.width).toEqual('576px');
      expect(backgroundEl.style.borderWidth).toEqual('1px');

    });

    test("The element's width should match even when the textbox is initially hidden", () => {
      let setDisplayPropertyOfFormGroups = function(property) {
        Array.prototype.forEach.call(
          document.getElementsByClassName('form-group'),
          element => element.style.display = property
        );
      };

      setDisplayPropertyOfFormGroups('none');

      window.GOVUK.notifyModules.start();

      setDisplayPropertyOfFormGroups('block');

      backgroundEl = textarea.nextElementSibling;
      expect(backgroundEl.style.width).toEqual('576px');

    });

    test("The element should be hidden from assistive technologies", () => {
      // start module
      window.GOVUK.notifyModules.start();

      expect(backgroundEl.getAttribute('aria-hidden')).toEqual('true');

    });

    test("If there is a variable in the content, its matching text in the element below should be wrapped in a highlight tag", () => {

      textarea.textContent  = "Dear ((title)) ((name))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(2);
      expect(highlightTags[0].textContent).toEqual('((title))');
      expect(highlightTags[1].textContent).toEqual('((name))');

    });

    test("Unless a data attribute is set to turn this feature off", () => {

      textarea.textContent  = "Dear ((title)) ((name))";
      textarea.setAttribute('data-highlight-placeholders', 'false')

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(0);

    });

    test("If there is optional text in the content, its matching text in the element below should be wrapped in a highlight tag", () => {

      textarea.textContent = "When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      const highlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

      expect(highlightTags.length).toEqual(2);
      expect(highlightTags[0].textContent).toEqual('((weekday??');
      expect(highlightTags[1].textContent).toEqual('((weekend??');

    });

    describe("Check autofocus behaviour", () => {

      test("The element should be focussed when 'data-autofocus-textbox attribute' is set to 'true'", () => {

        document.body.innerHTML = `
        <div class="govuk-form-group govuk-textarea-highlight">
          <label class="govuk-label" for="template_content">Message</label>
          <textarea class="govuk-textarea govuk-!-width-full govuk-textarea-highlight__textbox" id="template_content" name="template_content" rows="8" data-notify-module="enhanced-textbox" data-autofocus-textbox="true"></textarea>
        </div>`;
        window.GOVUK.notifyModules.start();

        textarea = document.querySelector('textarea');

        expect(document.activeElement).toBe(textarea);

      });

      test("The element should not be focussed when 'data-autofocus-textbox attribute' is set to 'false'", () => {

        document.body.innerHTML = `
        <div class="govuk-form-group govuk-textarea-highlight">
          <label class="govuk-label" for="template_content">Message</label>
          <textarea class="govuk-textarea govuk-!-width-full govuk-textarea-highlight__textbox" id="template_content" name="template_content" rows="8" data-notify-module="enhanced-textbox" data-autofocus-textbox="false"></textarea>
        </div>`;
        window.GOVUK.notifyModules.start();

        textarea = document.querySelector('textarea');

        expect(document.activeElement).not.toBe(textarea);

      });

      test("The element should not be focussed if 'data-autofocus-textbox attribute' is ommitted", () => {

        document.body.innerHTML = `
        <div class="govuk-form-group govuk-textarea-highlight">
          <label class="govuk-label" for="template_content">Message</label>
          <textarea class="govuk-textarea govuk-!-width-full govuk-textarea-highlight__textbox" id="template_content" name="template_content" rows="8" data-notify-module="enhanced-textbox"></textarea>
        </div>`;
        window.GOVUK.notifyModules.start();

        textarea = document.querySelector('textarea');

        expect(document.activeElement).not.toBe(textarea);

      });

    });

  });

  describe("When the content of the textbox is updated", () => {

    // doesn't apply to inputs as they have a fixed height
    test("If new input changes the textarea's height, the height of the element below should still match", () => {

      // set 10 lines of content
      textarea.textContent = `
      Ref: ((reference))
      Date: ((date))
      NHS number: ((nhs_number))

      Dear ((name))

      Thank you for attending the appointment on ((appointment_date)).

      We will now pass on the results to your GP, ((doctor)), who will be in contact with you soon to arrange a follow up appointment.

      `;

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add another line of text to the content
      textarea.textContent += "Best Regards\n\n((requester))";

      // mock calls for the background element's current height
      jest.spyOn(backgroundEl, 'offsetHeight', 'get').mockImplementation(() => 248);

      helpers.triggerEvent(textarea, 'input');

      expect(window.getComputedStyle(textarea).height).toEqual("248px");

    });

    test("If a resize changes the textarea's width, the width of the element below should still match", () => {
      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      expect(window.getComputedStyle(textarea).width).toEqual("576px");
      expect(window.getComputedStyle(backgroundEl).width).toEqual("576px");

      textarea.style.width = "500px"
      helpers.triggerEvent(window, 'resize');

      expect(window.getComputedStyle(textarea).width).toEqual("500px");
      expect(window.getComputedStyle(backgroundEl).width).toEqual("500px");

    });

    test("If a new variable is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      textarea.textContent = "Dear ((title)) ((name))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with a new variable
      textarea.textContent += "\nRef: ((reference))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(3);
      expect(highlightTags[2].textContent).toEqual('((reference))');

    });

    test("If a new piece of optional text is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      textarea.textContent = "Dear ((title)) ((name))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with some optional content inside
      textarea.textContent += "\nYour appointment will be on ((date)). When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');
      const optionalHighlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

      expect(highlightTags.length).toEqual(3);
      expect(optionalHighlightTags.length).toEqual(2);
      expect(optionalHighlightTags[0].textContent).toEqual('((weekday??');
      expect(optionalHighlightTags[1].textContent).toEqual('((weekend??');

    });

    test("If a variable is removed from the textbox, its highlight should also be removed", () => {

      textarea.textContent = `
        Dear ((title)) ((name))

        Ref: ((reference))`;

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with a new variable
      textarea.textContent = "Dear ((title)) ((name))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(2);
      expect(highlightTags[0].textContent).toEqual('((title))');
      expect(highlightTags[1].textContent).toEqual('((name))');

    });

    test("If a piece of optional text has been removed from the textbox, its highlight should also be removed", () => {

      textarea.textContent = `
        Dear ((title)) ((name))

        Your appointment will be on ((date)). When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance)).`;

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with a new variable
      textarea.textContent = `
        Dear ((title)) ((name))

        Your appointment will be on ((date)). When you arrive, please go to the ((weekday??main entrance))`;

      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');
      const optionalHighlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

      expect(highlightTags.length).toEqual(3);
      expect(optionalHighlightTags.length).toEqual(1);
      expect(highlightTags[0].textContent).toEqual('((title))');
      expect(highlightTags[1].textContent).toEqual('((name))');
      expect(optionalHighlightTags[0].textContent).toEqual('((weekday??');
      expect(highlightTags[2].textContent).toEqual('((date))');

    });

  });

  describe("When the content of the textbox is updated", () => {

    // doesn't apply to inputs as they have a fixed height
    test("If new input changes the textarea's height, the height of the element below should still match", () => {

      // set 10 lines of content
      textarea.textContent = `
      Ref: ((reference))
      Date: ((date))
      NHS number: ((nhs_number))

      Dear ((name))

      Thank you for attending the appointment on ((appointment_date)).

      We will now pass on the results to your GP, ((doctor)), who will be in contact with you soon to arrange a follow up appointment.

      `;

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add another line of text to the content
      textarea.textContent += "Best Regards\n\n((requester))";

      // mock calls for the background element's current height
      jest.spyOn(backgroundEl, 'offsetHeight', 'get').mockImplementation(() => 248);

      helpers.triggerEvent(textarea, 'input');

      expect(window.getComputedStyle(textarea).height).toEqual("248px");

    });

    test("If a resize changes the textarea's width, the width of the element below should still match", () => {
      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      expect(window.getComputedStyle(textarea).width).toEqual("576px");
      expect(window.getComputedStyle(backgroundEl).width).toEqual("576px");

      textarea.style.width = "500px"
      helpers.triggerEvent(window, 'resize');

      expect(window.getComputedStyle(textarea).width).toEqual("500px");
      expect(window.getComputedStyle(backgroundEl).width).toEqual("500px");

    });

    test("If a new variable is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      textarea.textContent = "Dear ((title)) ((name))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with a new variable
      textarea.textContent += "\nRef: ((reference))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(3);
      expect(highlightTags[2].textContent).toEqual('((reference))');

    });

    test("If a new piece of optional text is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      textarea.textContent = "Dear ((title)) ((name))";

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with some optional content inside
      textarea.textContent += "\nYour appointment will be on ((date)). When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');
      const optionalHighlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

      expect(highlightTags.length).toEqual(3);
      expect(optionalHighlightTags.length).toEqual(2);
      expect(optionalHighlightTags[0].textContent).toEqual('((weekday??');
      expect(optionalHighlightTags[1].textContent).toEqual('((weekend??');

    });

    test("If a variable is removed from the textbox, its highlight should also be removed", () => {

      textarea.textContent = `
        Dear ((title)) ((name))

        Ref: ((reference))`;

      // start module
      window.GOVUK.notifyModules.start();

      backgroundEl = textarea.nextElementSibling;

      // add some more content with a new variable
      textarea.textContent = "Dear ((title)) ((name))";
      helpers.triggerEvent(textarea, 'input');

      const highlightTags = backgroundEl.querySelectorAll('.placeholder');

      expect(highlightTags.length).toEqual(2);
      expect(highlightTags[0].textContent).toEqual('((title))');
      expect(highlightTags[1].textContent).toEqual('((name))');

    });

  });

});
