import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class FullscreenTable {

  constructor($module) {

    if (!isSupported()) {
      return this;
    }

    this.$module = $module;
    this.$table = this.$module.querySelector('table');

    this.nativeHeight = this.$module.offsetHeight + 20; // 20px for scrollbar room
    this.topOffset = this.$module.offsetTop;

    this.isFocusable = this.$table.getBoundingClientRect().width > this.$module.getBoundingClientRect().width;
    this.maintainHeight = this.maintainHeight.bind(this);
    this.maintainWidth = this.maintainWidth.bind(this);
    this.toggleShadows = this.toggleShadows.bind(this);

    this.insertShims();
    this.maintainWidth();
    this.maintainHeight();
    this.toggleShadows();

    window.addEventListener('scroll', this.maintainHeight);
    window.addEventListener('resize', this.maintainHeight);
    window.addEventListener('resize', this.maintainWidth);

    this.$scrollableTable.addEventListener('scroll', this.toggleShadows);
    this.$scrollableTable.addEventListener('scroll', this.maintainHeight);

    if (this.isFocusable) {
      const toggleFocusStyle = () => this.$module.classList.toggle('js-focus-style');
      this.$scrollableTable.addEventListener('focus', toggleFocusStyle);
      this.$scrollableTable.addEventListener('blur', toggleFocusStyle);
    }

    if (window.GOVUK.stickAtBottomWhenScrolling.recalculate) {
      window.GOVUK.stickAtBottomWhenScrolling.recalculate();
    }

    this.maintainWidth();
  }

  insertShims() {
    const caption = this.$table.querySelector('caption');
    const captionId = caption.textContent.toLowerCase().replace(/[^A-Za-z]+/g, '');
    caption.id = captionId;

    // Create the scrollable wrapper and move the table inside it
    const $scrollableWrapper = document.createElement('div');
    $scrollableWrapper.className = 'fullscreen-scrollable-table';
    if (this.isFocusable) {
      $scrollableWrapper.setAttribute('role', 'region');
      $scrollableWrapper.setAttribute('aria-labelledby', captionId);
      $scrollableWrapper.setAttribute('tabindex', '0');
    }
    this.$table.parentNode.insertBefore($scrollableWrapper, this.$table);
    $scrollableWrapper.appendChild(this.$table);

    // Create the fixed (frozen column) table by cloning the scrollable one
    const $fixedWrapper = $scrollableWrapper.cloneNode(true);
    $fixedWrapper.className = 'fullscreen-fixed-table';
    $fixedWrapper.removeAttribute('role');
    $fixedWrapper.removeAttribute('aria-labelledby');
    $fixedWrapper.removeAttribute('tabindex');
    $fixedWrapper.setAttribute('aria-hidden', 'true');
    $fixedWrapper.querySelector('caption')?.removeAttribute('id');

    // Create the shadow and shim elements
    const $rightShadow = document.createElement('div');
    $rightShadow.className = 'fullscreen-right-shadow';

    const $shim = document.createElement('div');
    $shim.className = 'fullscreen-shim';
    $shim.style.height = `${this.nativeHeight}px`;
    $shim.style.top = `${this.topOffset}px`;

    // Add new elements to the DOM
    this.$module.appendChild($fixedWrapper);
    this.$module.appendChild($rightShadow);
    this.$module.parentNode.insertBefore($shim, this.$module.nextSibling);
    this.$module.style.position = 'absolute';

    // Cache references to the new elements
    this.$scrollableTable = this.$module.querySelector('.fullscreen-scrollable-table');
    this.$fixedTable = this.$module.querySelector('.fullscreen-fixed-table');
    this.$rightShadow = this.$module.querySelector('.fullscreen-right-shadow');
  }

  maintainHeight() {
    const height = Math.min(
      (window.innerHeight - this.topOffset) + window.scrollY,
      this.nativeHeight
    );
  
    this.$scrollableTable.style.height = `${height}px`;
    this.$fixedTable.style.height = `${height}px`;
  }

  maintainWidth() {
    const $scrollableIndexColumnHeader = this.$scrollableTable.querySelector('.table-field-heading-first');
    const $fixedIndexColumnHeader = this.$fixedTable.querySelector('.table-field-heading-first');

    if ($scrollableIndexColumnHeader === null || $fixedIndexColumnHeader === null) return;

    this.$scrollableTable.style.width = `${this.$module.parentElement.getBoundingClientRect().width}px`;

    // Ensure column widths in both tables match to prevent misalignment
    if ($fixedIndexColumnHeader.getBoundingClientRect().width !== $scrollableIndexColumnHeader.getBoundingClientRect().width) {
      $scrollableIndexColumnHeader.style.width = `${$fixedIndexColumnHeader.getBoundingClientRect().width}px`;
    }

    // Set the width of the fixed table container to match its first column
    this.$fixedTable.style.width = `${$fixedIndexColumnHeader.getBoundingClientRect().width + 4}px`; // 4px for shadow
  }

  toggleShadows() {
    // Show a shadow on the frozen column if the table is scrolled left
    const isScrolled = this.$scrollableTable.scrollLeft > 0;
    this.$fixedTable.classList.toggle('fullscreen-scrolled-table', isScrolled);

    // Show a shadow on the right edge if there's more content to scroll to
    const maxScroll = this.$table.offsetWidth - this.$scrollableTable.offsetWidth;
    const isScrollable = this.$scrollableTable.scrollLeft < maxScroll;
    this.$rightShadow.classList.toggle('visible', isScrollable);

    setTimeout(() => this.$rightShadow.classList.add('with-transition'), 3000);
  }
}

export default FullscreenTable;
