// helpers for generating patterns of HTML

function getRadios (fields, name) {
  const result = '';

  return fields.map((field, idx) => {
    const count = idx + 1;
    const id = field.id || `${name}-${count}`;

    return `
      <div class="govuk-radios__item">
        <input class="govuk-radios__input" id="${id}" name="${name}" type="radio" value="${field.value}" ${field.checked ? 'checked' : ''}>
        <label class="govuk-label govuk-radios__label" for="${id}">
          ${field.label}
        </label>
      </div>`;
  }).join("\n");
};

function getRadioGroup (data) {
  let radioGroup = document.createElement('div');

  radioGroup.classList.add('govuk-form-group');
  if ('cssClasses' in data) {
    data.cssClasses.forEach(cssClass => radioGroup.classList.add(cssClass));
  }
  radioGroup.innerHTML = `
    <fieldset class="govuk-fieldset" id="${data.name}">
      <legend class="govuk-fieldset__legend${data.hideLegend ? " govuk-visually-hidden" : ""}">
        ${data.label}
      </legend>
      <div class="govuk-radios">
        ${getRadios(data.fields, data.name)}
      </div>
    </fieldset>`;

    return radioGroup;
};

function templatesAndFoldersCheckboxes (hierarchy) {
  let result = '';

  hierarchy.forEach((node, idx) => {

    result += `
      <div class="govuk-checkboxes__item template-list-item template-list-item-with-checkbox template-list-item-without-ancestors">
        <input class="govuk-checkboxes__input" id="templates-or-folder-${idx}" name="templates_and_folders" type="checkbox" value="templates-or-folder-${idx}">
        <label class="govuk-checkboxes__label template-list-item-label" for="templates-or-folder-${idx}">
          <span class="govuk-visually-hidden">${node.label}</span>
        </label>
        <a href="/services/6658542f-0cad-491f-bec8-ab8457700ead/templates/all/folders/3d057d9a-51fc-45ea-8b63-0003206350a6" class="govuk-link govuk-link--no-visited-state template-list-${node.type === 'folder' ? 'folder' : 'template'}">
          <span class="live-search-relevant">${node.label}</span>
        </a>
        ${node.meta}
      </div>`;

  });

  return result;

};

exports.getRadios = getRadios;
exports.getRadioGroup = getRadioGroup;
exports.templatesAndFoldersCheckboxes = templatesAndFoldersCheckboxes;
