(function(GOVUK, Modules) {
  "use strict";

  const interval = 1500; // milliseconds

  GOVUK.timeCache = {};
  GOVUK.resultCache = {};

  let getter = function(resource, render) {

    if (
      GOVUK.resultCache[resource] &&
      (Date.now() < GOVUK.timeCache[resource])
    ) {
      render(GOVUK.resultCache[resource]);
    } else {
      GOVUK.timeCache[resource] = Date.now() + interval;
      $.get(
        resource,
        response => render(GOVUK.resultCache[resource] = response)
      );
    }

  };

  let poller = (resource, key, component) => () => getter(
    resource, response => component.html(response[key])
  );

  Modules.UpdateContent = function() {

    this.start = function(component) {

      const $component = $(component);

      setInterval(
        poller($component.data('resource'), $component.data('key'), $component),
        interval / 5
      );

    };
  };

})(window.GOVUK, window.GOVUK.Modules);
