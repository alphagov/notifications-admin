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

  // Methods to ensure the DOM fragment is clean of classes added by JS before diffing
  // and that they are replaced afterwards.
  var classesPersister = {
    _classNames: [],
    _$els: [],
    addClassName: function (className) {
      if (this._classNames.indexOf(className) === -1) {
        this._classNames.push(className);
      }
    },
    remove: function () {
      this._classNames.forEach(className => {
        var $elsWithClassName = $('.' + className).removeClass(className);

        // store elements for that className at the same index
        this._$els.push($elsWithClassName);
      });
    },
    replace: function () {
      this._classNames.forEach((className, index) => {
        var $el = this._$els[index];

        // Avoid updating elements that are no longer present.
        // elements removed will still exist in memory but won't be attached to the DOM any more
        if (global.document.body.contains($el.get(0))) {
          $el.addClass(className);
        }
      });

      // remove references to elements
      this.$els = [];
    }
  };

  var getRenderer = ($contents, key) => response => {
    classesPersister.remove();
    morphdom(
      $contents.get(0),
      $(response[key]).get(0)
    );
    classesPersister.replace();
  };

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

    this.start = component => {
      var $component = $(component);
      var $contents = $component.children().eq(0);
      var key = $component.data('key');
      var resource = $component.data('resource');
      var form = $component.data('form');

      // replace component with contents
      // the renderer does this anyway when diffing against the first response
      $component.replaceWith($contents);

      // store any classes that should persist through updates
      if ($contents.data('classesToPersist') !== undefined) {
        $contents.data('classesToPersist')
          .split(' ')
          .forEach(className => classesPersister.addClassName(className));
      }

      setTimeout(
        () => poll(
          getRenderer($contents, key),
          resource,
          getQueue(resource),
          form
        ),
        defaultInterval
      );
    };

  };

  global.GOVUK.Modules.UpdateContent.calculateBackoff = calculateBackoff;

})(window);
