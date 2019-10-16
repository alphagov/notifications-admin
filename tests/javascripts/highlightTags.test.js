const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/highlightTags.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Highlight tags', () => {

  let input;
  let textarea;
  let backgroundEl;

  beforeAll(() => {

    // set some default styling
    const stylesheet = document.createElement('style');

    stylesheet.innerHTML = ".textbox-highlight-textbox { padding: 2px; width: 576px; border-width: 1px; }";
    stylesheet.innerHTML += "textarea.textbox-highlight-textbox { height: 224px; }";

    document.getElementsByTagName('head')[0].appendChild(stylesheet);

  });

  afterAll(() => {

    stylesheet.parentNode.removeChild(stylesheet);

  });

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <div class="form-group">
        <label for="subject">Subject</label>
        <input class="form-control textbox-highlight-textbox" data-module="highlight-tags" type="text" name="subject" id="subject" />
      </div>
      <div class="form-group">
        <label for="template_content">Message</label>
        <textarea class="form-control form-control-1-1 textbox-highlight-textbox" data-module="highlight-tags" id="template_content" name="template_content" rows="8">
        </textarea>
      </div>`;

    input = document.querySelector('input');
    textarea = document.querySelector('textarea');

  });

  afterEach(() => {

    document.body.innerHTML = '';

  });

  describe("When the page loads", () => {

    describe("An element should be added as a layer below the textbox to hold the highlights", () => {

      beforeEach(() => {

        // start module
        window.GOVUK.modules.start();

      });

      test("If the textbox is a <textarea>", () => {

        backgroundEl = textarea.nextElementSibling;

        // both the textbox and the element behind need a wrapping element
        expect(textarea.parentNode.classList.contains('textbox-highlight-wrapper')).toBe(true);

        expect(backgroundEl).not.toBeNull();
        expect(backgroundEl.classList.contains('textbox-highlight-background')).toBe(true);

      });

      test("If the textbox is an <input>", () => {

        backgroundEl = input.nextElementSibling;

        // both the textbox and the element behind need a wrapping element
        expect(input.parentNode.classList.contains('textbox-highlight-wrapper')).toBe(true);

        expect(backgroundEl).not.toBeNull();
        expect(backgroundEl.classList.contains('textbox-highlight-background')).toBe(true);

      });

    });

    describe("The element's dimensions and border-width should match those of the textbox", () => {

      beforeEach(() => {

        // start module
        window.GOVUK.modules.start();

      });

      test("If the textbox is an <textarea>", () => {

        backgroundEl = textarea.nextElementSibling;

        // element has box-sizing: border-box so width includes padding and border
        expect(backgroundEl.style.width).toEqual('582px');
        expect(backgroundEl.style.borderWidth).toEqual('1px');

      });

      test("If the textbox is an <input>", () => {

        backgroundEl = input.nextElementSibling;

        // element has box-sizing: border-box so width includes padding and border
        expect(backgroundEl.style.width).toEqual('582px');
        expect(backgroundEl.style.borderWidth).toEqual('1px');

      });

    });

    describe("The element's width should match even when the textbox is initially hidden", () => {

      beforeEach(() => {

        let setDisplayPropertyOfFormGroups = function(property) {
          Array.prototype.forEach.call(
            document.getElementsByClassName('form-group'),
            element => element.style.display = property
          );
        };

        setDisplayPropertyOfFormGroups('none');

        window.GOVUK.modules.start();

        setDisplayPropertyOfFormGroups('block');

      });

      test("If the textbox is an <textarea>", () => {

        backgroundEl = textarea.nextElementSibling;
        expect(backgroundEl.style.width).toEqual('582px');

      });

    });

    test("The element should be hidden from assistive technologies", () => {

      expect(backgroundEl.getAttribute('aria-hidden')).toEqual('true');

    });

    describe("If there is a variable in the content, its matching text in the element below should be wrapped in a highlight tag", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent  = "Dear ((title)) ((name))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = textarea.nextElementSibling;

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((title))');
        expect(highlightTags[1].textContent).toEqual('((name))');

      });

      test("If the textbox is a <input>", () => {

        input.value = "Dear ((title)) ((name))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((title))');
        expect(highlightTags[1].textContent).toEqual('((name))');

      });

      test("Unless a data attribute is set to turn this feature off", () => {

        textarea.textContent  = "Dear ((title)) ((name))";
        textarea.setAttribute('data-highlight-placeholders', 'false')

        // start module
        window.GOVUK.modules.start();

        backgroundEl = textarea.nextElementSibling;

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(0);

      });

    });

    describe("If there is optional text in the content, its matching text in the element below should be wrapped in a highlight tag", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent = "When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = textarea.nextElementSibling;

        const highlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((weekday??');
        expect(highlightTags[1].textContent).toEqual('((weekend??');

      });

      test("If the textbox is an <input>", () => {

        input.value = "When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        const highlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((weekday??');
        expect(highlightTags[1].textContent).toEqual('((weekend??');

      });

    });

  });

  describe("When the content of the textbox is updated", () => {

    // doesn't apply to inputs as they have a fixed height
    test("If new input changes the textarea's dimensions, the size of the element below should still match", () => {

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
      window.GOVUK.modules.start();

      backgroundEl = textarea.nextElementSibling;

      // add another line of text to the content
      textarea.textContent += "Best Regards\n\n((requester))";

      // mock calls for the background element's current height
      jest.spyOn(backgroundEl, 'offsetHeight', 'get').mockImplementation(() => 248);

      helpers.triggerEvent(textarea, 'input');

      expect(window.getComputedStyle(textarea).height).toEqual("248px");

    });

    describe("If a new variable is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent = "Dear ((title)) ((name))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = textarea.nextElementSibling;

        // add some more content with a new variable
        textarea.textContent += "\nRef: ((reference))";
        helpers.triggerEvent(textarea, 'input');

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(3);
        expect(highlightTags[2].textContent).toEqual('((reference))');

      });

      test("If the textbox is an <input>", () => {

        input.value = "Hospital appointment for ((name))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        // add some more content with a new variable
        input.value += ", ref: ((reference))";
        helpers.triggerEvent(input, 'input');

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((name))');
        expect(highlightTags[1].textContent).toEqual('((reference))');

      });

    });

    describe("If a new piece of optional text is added to the textbox, it should also be added to the element below in a highlight tag", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent = "Dear ((title)) ((name))";

        // start module
        window.GOVUK.modules.start();

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

      test("If the textbox is an <input>", () => {

        input.value = "Hospital appointment";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        // add some more content with some optional content inside
        input.value += "((important?? - IMPORTANT))";
        helpers.triggerEvent(input, 'input');

        const optionalHighlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

        expect(optionalHighlightTags.length).toEqual(1);
        expect(optionalHighlightTags[0].textContent).toEqual('((important??');

      });

    });

    describe("If a variable is removed from the textbox, its highlight should also be removed", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent = `
          Dear ((title)) ((name))

          Ref: ((reference))`;

        // start module
        window.GOVUK.modules.start();

        backgroundEl = textarea.nextElementSibling;

        // add some more content with a new variable
        textarea.textContent = "Dear ((title)) ((name))";
        helpers.triggerEvent(textarea, 'input');

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(2);
        expect(highlightTags[0].textContent).toEqual('((title))');
        expect(highlightTags[1].textContent).toEqual('((name))');

      });

      test("If the textbox is an <input>", () => {

        input.value = "Hospital appointment for ((name)), ref: ((reference))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        // add some more content with a new variable
        input.value = "Hospital appointment for ((name))";
        helpers.triggerEvent(input, 'input');

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');

        expect(highlightTags.length).toEqual(1);
        expect(highlightTags[0].textContent).toEqual('((name))');

      });

    });

    describe("If a piece of optional text has been removed from the textbox, its highlight should also be removed", () => {

      test("If the textbox is a <textarea>", () => {

        textarea.textContent = `
          Dear ((title)) ((name))

          Your appointment will be on ((date)). When you arrive, please go to the ((weekday??main entrance))((weekend??side entrance)).`;

        // start module
        window.GOVUK.modules.start();

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

      test("If the textbox is an <input>", () => {

        input.value = "Hospital appointment for ((name))((important?? - IMPORTANT))";

        // start module
        window.GOVUK.modules.start();

        backgroundEl = input.nextElementSibling;

        // add some more content with a new variable
        input.value = "Hospital appointment for ((name))"

        helpers.triggerEvent(input, 'input');

        const highlightTags = backgroundEl.querySelectorAll('.placeholder');
        const optionalHighlightTags = backgroundEl.querySelectorAll('.placeholder-conditional');

        expect(highlightTags.length).toEqual(1);
        expect(optionalHighlightTags.length).toEqual(0);
        expect(highlightTags[0].textContent).toEqual('((name))');

      });

    });

  });

});
