export default {
  extends: ["stylelint-config-standard-scss", "stylelint-config-gds/scss"],
  // do not use these rules. We need to decide to fix our css if we want to adhere to them
  rules: {
    "length-zero-no-unit": null,
    "color-hex-length": null,
    "color-named": null,
    "comment-empty-line-before": null,
    "max-nesting-depth": null,
    "value-keyword-case": null,
    "shorthand-property-no-redundant-values": null,
    "selector-attribute-quotes": null,
    "selector-pseudo-element-colon-notation": null,
    "selector-no-qualifying-type": null,
    "selector-pseudo-element-no-unknown": null,
    "no-duplicate-selectors": null,
    "rule-empty-line-before": null,
    "number-max-precision": null,
    "selector-max-id": null,
    "scss/comment-no-loud": null,
    "scss/dollar-variable-pattern": null,
    "scss/operator-no-unspaced": null,
    "declaration-block-no-shorthand-property-overrides": null,
    "scss/double-slash-comment-whitespace-inside": null,
    "declaration-property-value-keyword-no-deprecated": [
      true,
      { "ignoreKeywords": ["break-word"] }
    ]
  }
}