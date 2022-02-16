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
  //
  // Added to allow the use of JS, in main.js, to apply styles which in future could be
  // achieved with the :has pseudo-class. If :has is available in our supported browsers,
  // this can be removed in favour of a CSS-only solution.
  var ClassesPersister = function ($contents) {
    this._$contents = $contents;
    this._classNames = [];
    this._classesTo$ElsMap = {};
  };
  ClassesPersister.prototype.addClassName = function (className) {
    if (this._classNames.indexOf(className) === -1) {
      this._classNames.push(className);
    }
  };
  ClassesPersister.prototype.remove = function () {
    // Store references to any elements with class names to persist
    this._classNames.forEach(className => {
      var $elsWithClassName = $('.' + className, this._$contents).removeClass(className);

      if ($elsWithClassName.length > 0) {
        this._classesTo$ElsMap[className] = $elsWithClassName;
      }
    });
  };
  ClassesPersister.prototype.replace = function () {
    var className;

    for (className in this._classesTo$ElsMap) {
      this._classesTo$ElsMap[className].each((idx, el) => {

        // Avoid updating elements that are no longer present.
        // elements removed will still exist in memory but won't be attached to the DOM any more
        if (global.document.body.contains(el)) {
          $(el).addClass(className);
        }

      });
    }

    // remove references to elements
    this._classesTo$ElsMap = {};
  };

  var getRenderer = ($contents, key, classesPersister) => response => {
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
      var classesPersister = new ClassesPersister($contents);

      // Replace component with contents.
      // The renderer does this anyway when diffing against the first response
      $component.replaceWith($contents);

      // Store any classes that should persist through updates
      //
      // Added to allow the use of JS, in main.js, to apply styles which in future could be
      // achieved with the :has pseudo-class. If :has is available in our supported browsers,
      // this can be removed in favour of a CSS-only solution.
      if ($contents.data('classesToPersist') !== undefined) {
        $contents.data('classesToPersist')
          .split(' ')
          .forEach(className => classesPersister.addClassName(className));
      }

      setTimeout(
        () => poll(
          getRenderer($contents, key, classesPersister),
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
