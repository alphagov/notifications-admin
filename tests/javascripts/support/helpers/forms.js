
// helper for spying on the submit method on a form element
// JSDOM's implementation of submit just wraps a 'not implemented' error so we need to mock that to track calls to it
//
// * Remove when JSDOM implements submit on its form elements *
//
// elements in JSDOM have a public API and a private implementation API, only used by internal code
// For form elements, these are instances of the following classes:
// - HTMLFormElement
// - HTMLFormElementImpl
//
// form elements link to their implementation instance via a symbol property
// this spies on the submit method of the implementation instance for a form element and mocks it to prevent 'not implemented' errors
function spyOnFormSubmit (jest, form) {

  const formImplementationSymbols = Object.getOwnPropertySymbols(form).filter(
    symbol => form[symbol].constructor.name === 'HTMLFormElementImpl'
  );

  if (!formImplementationSymbols.length) {
    throw Error("Error mocking form.submit: symbol reference to HTMLFormElementImpl instance not found on form element");
  }

  const HTMLFormElementImpl = form[formImplementationSymbols[0]];

  const submitSpy = jest.spyOn(HTMLFormElementImpl, 'submit')

  submitSpy.mockImplementation();
  return submitSpy;

};

exports.spyOnFormSubmit = spyOnFormSubmit;
