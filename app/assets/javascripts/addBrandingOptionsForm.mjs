import { NotifyModules } from './modules.mjs';

// Factory function to create instances of LiveCheckboxControls with altered methods
NotifyModules.AddBrandingOptionsForm = function() {
  // Set up 'this' object as an instance of LiveCheckboxControls
  NotifyModules.LiveCheckboxControls.call(this);

  // Overwrite method on instance object
  this.onNothingSelected = function (state) {};
};
