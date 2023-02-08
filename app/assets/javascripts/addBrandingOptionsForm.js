(function(Modules) {
  "use strict";

  // Factory function to create instances of LiveCheckboxControls with altered methods
  Modules.AddBrandingOptionsForm = function() {
    // Set up 'this' object as an instance of LiveCheckboxControls
    Modules.LiveCheckboxControls.call(this);

    // Overwrite method on instance object
    this.onNothingSelected = function (state) {};
  };

})(window.GOVUK.NotifyModules);
