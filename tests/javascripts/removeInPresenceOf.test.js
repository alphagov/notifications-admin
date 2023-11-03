beforeAll(() => {
  require('../../app/assets/javascripts/removeInPresenceOf.js')
});

afterAll(() => {
  require('./support/teardown.js');
});

describe("Remove in presence of", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <main id="main-content">
        <div id="old-content" data-notify-module="remove-in-presence-of" data-target-element-id="new-content">old content</div>
      </main>
    `;
    window.GOVUK.notifyModules.start();
  });

  describe("The page", () => {

    test("Has the existing element on load", () => {
      expect(document.getElementById('old-content')).not.toBeNull();
    });

    test("Removes the existing element when a new element is added", async () => {

      let outcome = new Promise((resolve, reject) => {
        setTimeout(() => {
          expect(document.getElementById('new-content')).not.toBeNull();
          expect(document.getElementById('old-content')).toBeNull();
          resolve();
        }, 0);
      });
      let newContent = document.createElement("div");

      newContent.id = "new-content";

      document.getElementById("main-content").append(newContent);

      await outcome;

    });
  });

});
