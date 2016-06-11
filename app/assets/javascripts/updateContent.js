(function(Modules) {
  "use strict";

  var queues = {};
  var dd = new diffDOM();

  var getRenderer = $component => response => dd.apply(
    $component.get(0),
    dd.diff($component.get(0), $(response[$component.data('key')]).get(0))
  );

  var getQueue = resource => (
    queues[resource] = queues[resource] || []
  );

  var flushQueue = function(queue, response) {
    while(queue.length) queue.shift()(response);
  };

  var poll = function(renderer, resource, queue, interval) {

    if (queue.push(renderer) === 1) $.get(
      resource,
      response => flushQueue(queue, response)
    );

    setTimeout(
      () => poll(...arguments), interval
    );

  };

  Modules.UpdateContent = function() {

    this.start = component => poll(
      getRenderer($(component)),
      $(component).data('resource'),
      getQueue($(component).data('resource')),
      ($(component).data('interval-seconds') || 1.5) * 1000
    );

  };

})(window.GOVUK.Modules);
