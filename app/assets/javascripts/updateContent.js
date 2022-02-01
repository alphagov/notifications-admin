(function(global) {
  "use strict";

  var queues = {};
  var morphdom = global.GOVUK.vendor.morphdom;
  var defaultInterval = 2000;
  var interval = 0;

  var calculateBackoff = responseTime => parseInt(Math.max(
      (250 * Math.sqrt(responseTime)) - 1000,
      1000
  ));

  var getRenderer = $component => response => morphdom(
    $component.get(0),
    $(response[$component.data('key')]).get(0)
  );

  var getQueue = resource => (
    queues[resource] = queues[resource] || []
  );

  var flushQueue = function(queue, response) {
    while(queue.length) queue.shift()(response);
  };

  var clearQueue = queue => (queue.length = 0);

  var poll = function(renderer, resource, queue, form) {

    let startTime = Date.now();

    if (document.visibilityState !== "hidden" && queue.push(renderer) === 1) $.ajax(
      resource,
      {
        'method': form ? 'post' : 'get',
        'data': form ? $('#' + form).serialize() : {}
      }
    ).done(
      response => {
        flushQueue(queue, response);
        if (response.stop === 1) {
          poll = function(){};
        }
        interval = calculateBackoff(Date.now() - startTime);
      }
    ).fail(
      () => poll = function(){}
    );

    setTimeout(
      () => poll.apply(window, arguments), interval
    );
  };

  global.GOVUK.Modules.UpdateContent = function() {

    this.start = component => setTimeout(
      () => poll(
        getRenderer($(component)),
        $(component).data('resource'),
        getQueue($(component).data('resource')),
        $(component).data('form')
      ),
      defaultInterval
    );

  };

  global.GOVUK.Modules.UpdateContent.calculateBackoff = calculateBackoff;

})(window);
