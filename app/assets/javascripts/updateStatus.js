(function(window) {
  "use strict";

  window.GOVUK.Modules.UpdateStatus = function() {

    const getRenderer = $component => response => $component.html(
      response.html
    );

    const throttle = (func, limit) => {

      let throttleOn = false;
      let callsHaveBeenThrottled = false;
      let timeout;

      return function() {

        const args = arguments;
        const context = this;

        if (throttleOn) {
          callsHaveBeenThrottled = true;
        } else {
          func.apply(context, args);
          throttleOn = true;
        }

        clearTimeout(timeout);

        timeout = setTimeout(() => {
          throttleOn = false;
          if (callsHaveBeenThrottled) func.apply(context, args);
          callsHaveBeenThrottled = false;
        }, limit);

      };

    };

    this.start = component => {

      let id = 'update-status';

      this.$component = $(component);
      this.$textbox = $('#' + this.$component.data('target'));

      this.$component
        .attr('id', id);

      this.$textbox
        .attr(
          'aria-describedby',
          (
            this.$textbox.attr('aria-describedby') || ''
          ) + (
            this.$textbox.attr('aria-describedby') ? ' ' : ''
          ) + id
        )
        .on('input', throttle(this.update, 150))
        .trigger('input');

    };

    this.update = () => {

      $.ajax(
        this.$component.data('updates-url'),
        {
          'method': 'post',
          'data': this.$textbox.parents('form').serialize()
        }
      ).done(
        getRenderer(this.$component)
      ).fail(
        () => {}
      );

    };

  };

})(window);
