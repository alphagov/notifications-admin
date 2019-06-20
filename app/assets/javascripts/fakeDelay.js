(function(Modules) {
  "use strict";

  Modules.FakeDelay = function() {
    this.start = function(component) {

      let $component = $(component),
          cache = $(component).html(),
          cssClass = $component.data('progress') ? 'loading-indicator' : 'hint';

      $component.html('<span class="' + cssClass + '">' + $component.data('message') + '</span>');

      setTimeout(function(){
        console.log('timeout')
        $component.html(cache);
      }, $component.data('timeout'))

    };
  };

})(window.GOVUK.Modules);
