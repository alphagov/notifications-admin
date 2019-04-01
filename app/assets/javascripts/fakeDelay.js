(function(Modules) {
  "use strict";

  Modules.FakeDelay = function() {
    this.start = function(component) {

      let $component = $(component),
          cache = $(component).html();

      $component.html('<span class="hint">' + $component.data('message') + '</span>');

      console.log($component);
      console.log($component.data('timeout'));
      console.log($component.data('message'));

      setTimeout(function(){
        console.log('timeout')
        $component.html(cache);
      }, $component.data('timeout'))

    };
  };

})(window.GOVUK.Modules);
