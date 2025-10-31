(function(global) {
  "use strict";

  var queues = {};
  var timeouts = {};
  var defaultInterval = 2000;
  var intervals = {};

  var calculateBackoff = responseTime => parseInt(Math.max(
      (250 * Math.sqrt(responseTime)) - 1000,
      1000
  ));

  var getRenderer = ($contents, key) => response => {
    var contents = $contents.get(0);
    var contentHasUpdated = false;
    window.Morphdom(
      contents,
      $(response[key]).get(0),
      {
        onBeforeElUpdated: function(fromEl, toEl) {
          // spec - https://dom.spec.whatwg.org/#concept-node-equals
          if (fromEl.isEqualNode(toEl)) {
            return false;
          } else if (fromEl === contents) { // if root node is different, updates will apply
            contentHasUpdated = true;
          }

          return true;
        }
      }
    );
    if (contentHasUpdated === true) {
      $(document).trigger("updateContent.onafterupdate", [contents]);
    }
  };

  var getQueue = resource => (
    queues[resource] = queues[resource] || []
  );

  var flushQueue = function(queue, response) {
    while(queue.length) queue.shift()(response);
  };

  var clearQueue = queue => (queue.length = 0);

  var poll = function(renderer, resource, queue, form) {
    let timeout;
    let startTime = Date.now();

    // Only send requests when window/tab is in use and nothing in queue
    if (document.visibilityState !== "hidden" && queue.push(renderer) === 1) {
      $.ajax(
        resource,
        {
          'method': form ? 'post' : 'get',
          'data': form ? $('#' + form).serialize() : {}
        }
      ).done(
        response => {
          flushQueue(queue, response);
          if (response.stop === 1) {
            window.clearTimeout(timeout); // stop polling
          } else {
            intervals[resource] = calculateBackoff(Date.now() - startTime); // keep polling but adjust for response time
          }
        }
      ).fail(
        response => {
          window.clearTimeout(timeout); // stop polling
          clearQueue(queue);
          if (response.status === 401) {
            window.location.reload();
          }
        }
      );
    }

    timeout = window.setTimeout(
      () => poll.apply(window, arguments), intervals[resource]
    );
  };

  global.GOVUK.NotifyModules.UpdateContent = function() {

    this.start = component => {
      var $component = $(component);
      var $contents = $component.children().eq(0);
      var key = $component.data('key');
      var resource = $component.data('resource');
      var form = $component.data('form');
      intervals[resource] = defaultInterval;

      // Replace component with contents.
      // The renderer does this anyway when diffing against the first response
      $component.replaceWith($contents);

      timeouts[resource] = setTimeout(
        () => poll(
          getRenderer($contents, key),
          resource,
          getQueue(resource),
          form
        ),
        intervals[resource]
      );
    };

  };

  global.GOVUK.NotifyModules.UpdateContent.calculateBackoff = calculateBackoff;

})(window);
