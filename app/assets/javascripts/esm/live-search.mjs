import { isSupported } from 'govuk-frontend';

class LiveSearch {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$module = $module;

    this.$searchBox = this.$module.querySelector('input');
    this.$searchLabel = this.$module.querySelector('label');
    this.$liveRegion = this.$module.querySelector('.live-search__status');
    this.$targets = document.querySelectorAll(this.$module.dataset.targets);
    this.state = 'loaded';


    this.$searchBox.addEventListener("input", () => {
      this.filter(this.$searchBox, this.$searchLabel, this.$liveRegion, this.$targets);
    });

    this.filter(this.$searchBox, this.$searchLabel, this.$liveRegion, this.$targets);

  }

  filter ($searchBox, $searchLabel, $liveRegion, $targets) {

    let query = this.normalize(this.$searchBox.value);
    let results = 0;

    $targets.forEach(($node) => {

      let content = $node.querySelector('.live-search-relevant') ? $node.querySelector('.live-search-relevant').textContent : $node.textContent;
      let isMatch = this.normalize(content).includes(this.normalize(query));
      // if there is a child node with checked state
      if ($node.querySelectorAll(':checked').length > 0) {
        if ($node.hasAttribute('hidden')) {
          $node.removeAttribute('hidden');
        }
        results++;
        return;
      }

      if (query == '') {
        if ($node.hasAttribute('hidden')) {
          $node.removeAttribute('hidden');
        }
        // specific to template list as we have items hidden by default in css
        // (items with ancestors) that we need to show if they match the search query
        // but also hide them back when there is no search query
        if ($node.classList.contains('visible-as-matches-search-query')) {
          $node.classList.remove('visible-as-matches-search-query');
        }
        results++;
        return;
      }

      if (isMatch) {
        $node.removeAttribute('hidden');
        // specific to template list as we have items hidden by default in css
        // (items with ancestors) that we need to show if they match the search query
        // we do that by applying a new class with display block property
        if ($node.classList.contains('template-list-item-hidden-by-default')) {
          $node.classList.add('visible-as-matches-search-query');
        }
      } else {
        $node.setAttribute('hidden', '');
        // specific to template list as we have items hidden by default in css
        // (items with ancestors) that we now need to hide again when they don't
        // match the search criteria
        if ($node.classList.contains('visible-as-matches-search-query')) {
          $node.classList.remove('visible-as-matches-search-query');
        }
      };

      if (isMatch) {
        results++; 
      }

    });

    if (this.state === 'loaded') {
      if (query !== '') {
       $searchBox.setAttribute('aria-label', $searchLabel.textContent.trim() + ', ' + this.resultsSummary(results));
      }
      this.state = 'active';
    } else {
      $searchBox.removeAttribute('aria-label');
      $liveRegion.textContent = this.resultsSummary(results);
    }

    // make sticky JS recalculate its cache of the element's position
    // because live search can change the height document
    if ('stickAtBottomWhenScrolling' in window.GOVUK) {
      window.GOVUK.stickAtBottomWhenScrolling.recalculate();
    }

  }

  normalize (string) {
    return string.toLowerCase().replace(/ /g,'');
  }

  resultsSummary (num) {
    if (num === 0) {
      return "no results";
    } else {
      return num + (num === 1 ? " result" : " results");
    }
  };
}

export default LiveSearch;
