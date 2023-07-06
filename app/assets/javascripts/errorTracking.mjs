import 'jquery';
import { NotifyModules } from './modules.mjs';
import { analytics } from './analytics/init.mjs';

NotifyModules.TrackError = function() {

  this.start = function(component) {

    if (analytics === null) return;

    analytics.trackEvent(
      'Error',
      $(component).data('error-type'),
      {
        'label': $(component).data('error-label')
      }
    );

  };

};
