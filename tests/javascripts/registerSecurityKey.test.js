beforeAll(() => {
  require('../../app/assets/javascripts/registerSecurityKey.js');
})

afterAll(() => {
  require('./support/teardown.js');
})

describe('Register security key', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <a href="#" role="button" draggable="false" class="govuk-button govuk-button--secondary" data-module="register-security-key">
        Register a key
      </a>`;
  })

  test('it is not implemented yet', () => {
    window.GOVUK.modules.start();
    jest.spyOn(window, 'alert').mockImplementation(() => {});

    button = document.querySelector('[data-module="register-security-key"]');
    button.click();

    expect(window.alert).toBeCalledWith('not implemented')
  })
})
