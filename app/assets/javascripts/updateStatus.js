(function(window) {
  "use strict";

  window.GOVUK.Modules.UpdateStatus = function() {

    let getRenderer = $component => response => $component.html(
      response.html
    );

    this.start = component => {

      let id = 'update-status';

      this.$component = $(component);
      this.$textbox = $('#' + this.$component.data('target'));

      this.$component
        .attr('id', id);

      this.$textbox
        .attr('aria-described-by', this.$textbox.attr('aria-described-by') + ' ' + id)
        .on('input', this.update)
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
