(function (Modules) {

  'use strict';

  Modules.RemoveInPresenceOf = function () {

    let elementToRemove;
    let observer = new MutationObserver(function () {
      if (document.getElementById(elementToRemove.dataset.targetElementId)) {
        elementToRemove.parentNode.removeChild(elementToRemove);
        observer.disconnect();
      }
    });

    this.start = function ($elementToRemove) {

      elementToRemove = $elementToRemove[0];
      observer.observe(document.getElementById('main-content'), { childList: true, subtree: true });

    };

  };
})(window.GOVUK.NotifyModules);
