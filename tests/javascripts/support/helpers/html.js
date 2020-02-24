// helpers for generating patterns of HTML

function getRadios (fields, name) {
  const result = '';

  return fields.map((field, idx) => {
    const count = idx + 1;

    return `
      <div class="multiple-choice">
        <input id="${name}-1" name="${name}" type="radio" value="${field.value}" ${field.checked ? 'checked' : ''}>
        <label class="block-label" for="${name}-1">
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
      <fieldset id="${data.name}">
        <legend class="form-label">
          ${data.label}
        </legend>
        ${getRadios(data.fields, data.name)}
      </fieldset>
    </div>`;

    return radioGroup;
};

function templatesAndFoldersCheckboxes (hierarchy) {
  let result = '';

  hierarchy.forEach((node, idx) => {

    result += `
      <div class="template-list-item template-list-item-with-checkbox  template-list-item-without-ancestors">
        <div class="multiple-choice">
          <input id="templates-or-folder-${idx}" name="templates_and_folders" type="checkbox" value="templates-or-folder-${idx}">
          <label></label>
        </div>
        <h2 class="message-name">
          <a href="/services/6658542f-0cad-491f-bec8-ab8457700ead/templates/all/folders/3d057d9a-51fc-45ea-8b63-0003206350a6" class="template-list-${node.type === 'folder' ? 'folder' : 'template'}">
            <span class="live-search-relevant">${node.label}</span>
          </a>
        </h2>
        ${node.meta}
      </div>`;

  });

  return result;

};

exports.getRadios = getRadios;
exports.getRadioGroup = getRadioGroup;
exports.templatesAndFoldersCheckboxes = templatesAndFoldersCheckboxes;
