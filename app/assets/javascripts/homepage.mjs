import 'jquery';
import { NotifyModules } from './modules.mjs';

window.GOVUK.NotifyModules.Homepage = function() {

  this.start = function(component) {

    let $component = $(component);
    let iterations = 0;
    let timeout = null;

    $component.on('click', () => {
      if (++iterations == 5) {
        $component.toggleClass('product-page-intro-wrapper--alternative');
      }
      clearTimeout(timeout);
      timeout = setTimeout(() => iterations = 0, 1500);
    });

  };

};
