(function(Modules) {
  "use strict";

  let state;
  let normalize = (string) => string.toLowerCase().replace(/ /g,'');
  let resultsSummary = (num) => {
    if (num === 0) {
      return "no results";
    } else {
      return num + (num === 1 ? " result" : " results");
    }
  };

  let filter = ($searchBox, $searchLabel, $liveRegion, $targets) => () => {

    let query = normalize($searchBox.val());
    let results = 0;

    $targets.each(function() {

      let content = $('.live-search-relevant', this).text() || $(this).text();
      let isMatch = normalize(content).indexOf(normalize(query)) > -1;

      if ($(this).has(':checked').length) {
        $(this).show();
        results++;
        return;
      }

      if (query == '') {
        $(this).css('display', '');
        results++;
        return;
      }

      $(this).toggle(isMatch);

      if (isMatch) { results++; }

    });

    if (state === 'loaded') {
      if (query !== '') {
        $searchBox.attr('aria-label', $searchLabel.text().trim() + ', ' + resultsSummary(results));
      }
      state = 'active';
    } else {
      $searchBox.removeAttr('aria-label');
      $liveRegion.text(resultsSummary(results));
    }

    // make sticky JS recalculate its cache of the element's position
    // because live search can change the height document
    if ('stickAtBottomWhenScrolling' in GOVUK) {
      GOVUK.stickAtBottomWhenScrolling.recalculate();
    }

  };


  Modules.LiveSearch = function() {

    this.start = function(component) {

      let $component = $(component);

      let $searchBox = $('input', $component);
      let $searchLabel = $('label', $component);
      let $liveRegion = $('.live-search__status', $component);

      let filterFunc = filter(
        $searchBox,
        $searchLabel,
        $liveRegion,
        $($component.data('targets'))
      );

      state = 'loaded';

      $searchBox.on('keyup input', filterFunc);

      filterFunc();

    };

  };

})(window.GOVUK.Modules);
