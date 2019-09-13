// helpers for generating patterns of HTML

function getRadios (fields) {
  const result = '';

  return fields.map((field, idx) => {
    const count = idx + 1;

    return `
      <div class="multiple-choice">
        <input id="choose-${field.name}-1" name="choose-${field.name}-1" type="radio" value="${field.value}" ${field.checked ? 'checked' : ''}>
        <label class="block-label" for="choose-${field.name}-1">
          ${field.label}
        </label>
      </div>`;
  }).join("\n");
};

function getRadioGroup (data) {
  let radioGroup = document.createElement('div');

  data.cssClasses.forEach(cssClass => radioGroup.classList.add(cssClass));
  radioGroup.innerHTML = `
    <div class="form-group ">
      <fieldset id="choose-${data.name}">
        <legend class="form-label">
           Choose ${data.label}
        </legend>
        ${getRadios(data.fields)}
      </fieldset>
    </div>`;

    return radioGroup;
};

exports.getRadios = getRadios;
exports.getRadioGroup = getRadioGroup;
