import RemoveInPresenceOf from '../../app/assets/javascripts/esm/remove-in-presence-of.mjs';
import { jest } from '@jest/globals';

describe("Remove in presence of", () => {
  beforeEach(() => {
    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <main id="main-content">
        <div id="old-content" data-notify-module="remove-in-presence-of" data-target-element-id="new-content">old content</div>
      </main>
    `;
    new RemoveInPresenceOf(document.querySelector('[data-notify-module="remove-in-presence-of"]'))
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
