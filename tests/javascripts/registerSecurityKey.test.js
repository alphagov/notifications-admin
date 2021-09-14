beforeAll(() => {
  window.CBOR = require('../../node_modules/cbor-js/cbor.js')
  require('../../app/assets/javascripts/registerSecurityKey.js')

  // populate missing values to allow consistent jest.spyOn()
  window.fetch = () => {}
  window.navigator.credentials = { create: () => { } }
  window.GOVUK.ErrorBanner = {
    showBanner: () => { },
    hideBanner: () => { }
  };
})

afterAll(() => {
  require('./support/teardown.js')

  // restore window attributes to their original undefined state
  delete window.fetch
  delete window.navigator.credentials
})

describe('Register security key', () => {
  let button

  beforeEach(() => {
    // disable console.error() so we don't see it in test output
    // you might need to comment this out to debug some failures
    jest.spyOn(console, 'error').mockImplementation(() => {})

    document.body.innerHTML = `
      <a href="#" role="button" draggable="false" class="govuk-button govuk-button--secondary" data-module="register-security-key">
        Register a key
      </a>`

    button = document.querySelector('[data-module="register-security-key"]')
    window.GOVUK.modules.start()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('creates a new credential and reloads', (done) => {

    jest.spyOn(window, 'fetch').mockImplementationOnce((_url) => {
      // initial fetch of options from the server
      // options from the server are CBOR-encoded
      const webauthnOptions = window.CBOR.encode('options')

      return Promise.resolve({
        ok: true, arrayBuffer: () => webauthnOptions
      })
    })

    jest.spyOn(window.navigator.credentials, 'create').mockImplementation((options) => {
      expect(options).toEqual('options')

      // fake PublicKeyCredential response from WebAuthn API
      // both of the nested properties are Array(Buffer) objects
      return Promise.resolve({
        response: {
          attestationObject: [1, 2, 3],
          clientDataJSON: [4, 5, 6],
        }
      })
    })

    jest.spyOn(window, 'fetch').mockImplementationOnce((_url, options) => {
      // subsequent POST of credential data to server
      const decodedData = window.CBOR.decode(options.body)
      expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4,5,6]))
      expect(decodedData.attestationObject).toEqual(new Uint8Array([1,2,3]))
      expect(options.headers['X-CSRFToken']).toBe()
      return Promise.resolve({ ok: true })
    })

    jest.spyOn(window.location, 'reload').mockImplementation(() => {
      // signal that the async promise chain was called
      done()
    })

    // this will make the test fail if the error banner is displayed
    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done('didnt expect the banner to be shown')
    })

    button.click()
  })

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn options fails (%s error)', (errorType, done) => {
    jest.spyOn(window, 'fetch').mockImplementation((_url) => {
      if (errorType == 'network') {
        return Promise.reject('error')
      } else {
        return Promise.resolve({ ok: false, statusText: 'error' })
      }
    })

    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done()
    })

    button.click()
  })

  test.each([
    ['network'],
    ['server'],
  ])('errors if sending WebAuthn credentials fails (%s)', (errorType, done) => {

    jest.spyOn(window, 'fetch').mockImplementationOnce((_url) => {
      // initial fetch of options from the server
      const webauthnOptions = window.CBOR.encode('options')

      return Promise.resolve({
        ok: true, arrayBuffer: () => webauthnOptions
      })
    })

    jest.spyOn(window.navigator.credentials, 'create').mockImplementation(() => {
      // fake PublicKeyCredential response from WebAuthn API
      return Promise.resolve({ response: {} })
    })

    jest.spyOn(window, 'fetch').mockImplementationOnce((_url) => {
      // subsequent POST of credential data to server
      switch (errorType) {
        case 'network':
          return Promise.reject('error')
        case 'server':
          return Promise.resolve({ ok: false, statusText: 'FORBIDDEN' })
      }
    })

    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done()
    })

    button.click()
  })

  test('errors if comms with the authenticator fails', (done) => {
    jest.spyOn(window.navigator.credentials, 'create').mockImplementation(() => {
      return Promise.reject(new DOMException('error'))
    })

    jest.spyOn(window, 'fetch').mockImplementation((_url) => {
      // initial fetch of options from the server
      const webauthnOptions = window.CBOR.encode('options')

      return Promise.resolve({
        ok: true, arrayBuffer: () => webauthnOptions
      })
    })

    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done()
    })

    button.click()
  })
})
