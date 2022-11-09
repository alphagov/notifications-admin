(function (Modules) {

  'use strict';

  Modules.RadiosWithImages = function () {

    this.handleImageClick = function () {
      const image_id = this.id;
      const image_input = document.querySelector('[aria-describedby="' + image_id + '"]');
      image_input.checked = true;
      image_input.focus();
    };

    this.start = function ($radioImage) {

      var radioImageNode = $radioImage.get(0);
      console.log(radioImageNode);

      radioImageNode.addEventListener('click', this.handleImageClick);
      radioImageNode.style.cursor = 'pointer';

    };

  };
})(window.GOVUK.NotifyModules);
