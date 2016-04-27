(function(GOVUK, Modules) {
  "use strict";

  GOVUK.timeCache = {};
  GOVUK.resultCache = {};

  var dd = new diffDOM();

  let getter = function(resource, interval, render) {

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

  let poller = (resource, key, $component, interval) => () => getter(
    resource, interval, response => dd.apply(
      $component.get(0),
      dd.diff($component.get(0), $(response[key]).get(0))
    )
  );

  Modules.UpdateContent = function() {

    this.start = function(component) {

      const $component = $(component);
      interval = ($(component).data("interval-seconds") * 1000) || 1500;

      setInterval(
        poller($component.data('resource'), $component.data('key'), $component, interval),
        interval / 5
      );

    };
  };

})(window.GOVUK, window.GOVUK.Modules);
