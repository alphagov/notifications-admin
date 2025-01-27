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

class PreviewPane {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.branding_style = $module.value;
    this.$form = $module.form;
    this.$paneWrapper = this.$form.querySelector('.govuk-grid-column-full');
    this.previewType = this.$form.dataset.previewType;
    this.letterBrandingPreviewRootPath = `templates/${this.previewType}-preview-image`;

    this.applyPreviewPane(this.previewType);
    
    this.$form.setAttribute('action', location.pathname.replace(new RegExp(`set-${this.previewType}-branding$`), `preview-${this.previewType}-branding`));
    this.$form.querySelector('button').textContent = 'Save';

    this.$form.querySelector('fieldset').addEventListener("change", (e) => {
      if (e.target.matches('input[name="branding_style"]')) {
        this.setPreviewPane(e.target);
      }
    });
  }

  applyPreviewPane(previewType) {
    previewType === 'letter' ? this.generateImagePreview() : this.generateIframePreview();
  }

  // we want to generate this just-in-time as otherwise
  // once the image is appended, src does a http request
  // even if the previewType is letter
  generateImagePreview() {
    let imagePreviewPane = document.createElement('div');
    imagePreviewPane.setAttribute('class','branding-preview-image');
    let imagePreviewPaneImage = document.createElement('img');
    imagePreviewPaneImage.setAttribute('alt','Preview of selected letter branding');
    imagePreviewPaneImage.setAttribute('src', `/${this.letterBrandingPreviewRootPath}?${this.buildQueryString(["branding_style", this.branding_style])}`);
    imagePreviewPane.appendChild(imagePreviewPaneImage);
    this.$paneWrapper.append(imagePreviewPane);
  }

  generateIframePreview() {
    let iframePreviewPane = document.createElement('iframe');
    iframePreviewPane.setAttribute('class','branding-preview');
    iframePreviewPane.setAttribute('scrolling','no');
    iframePreviewPane.setAttribute('src',`/_${this.previewType}?${this.buildQueryString(['branding_style', this.branding_style])}`);
    this.$paneWrapper.append(iframePreviewPane);
  }

  buildQueryString () {
    // we can accept multiple arrays of parameters
    // but here we only have 2
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/arguments
    const data = Array.from(arguments);
    return data.map((val, _idx) => `${encodeURI(val[0])}=${encodeURI(val[1])}`).join('&');
  }
  
  setPreviewPane ($target) {
    this.branding_style = $target.value;
    this.previewType === 'letter' ?
      this.$paneWrapper.querySelector('img').setAttribute('src', `/${this.letterBrandingPreviewRootPath}?${this.buildQueryString(['branding_style', this.branding_style])}`)
    :
      this.$paneWrapper.querySelector('iframe').setAttribute('src', `/_${this.previewType}?${this.buildQueryString(['branding_style', this.branding_style])}`);
    ;
  }
}

export default PreviewPane;
