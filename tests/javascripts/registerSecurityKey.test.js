beforeAll(() => {
  window.CBOR = require('../../node_modules/cbor-js/cbor.js')
  require('../../app/assets/javascripts/registerSecurityKey.js')

  // disable console.error() so we don't see it in test output
  // you might need to comment this out to debug some failures
  jest.spyOn(console, 'error').mockImplementation(() => {})

  // ensure window.alert() is implemented to simplify errors
  jest.spyOn(window, 'alert').mockImplementation(() => {})

  // populate missing values to allow consistent jest.spyOn()
  window.fetch = () => {}
  window.navigator.credentials = { create: () => {} }
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
    document.body.innerHTML = `
      <a href="#" role="button" draggable="false" class="govuk-button govuk-button--secondary" data-module="register-security-key">
        Register a key
      </a>`

    button = document.querySelector('[data-module="register-security-key"]')
    window.GOVUK.modules.start()
  })

  test('creates a new credential and reloads', (done) => {
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

    jest.spyOn(window.location, 'reload').mockImplementation(() => {
      // signal that the async promise chain was called
      done()
    })

    jest.spyOn(window, 'fetch').mockImplementation((_url, options = {}) => {
      // initial fetch of options from the server
      if (!options.method) {
        // options from the server are CBOR-encoded
        webauthnOptions = window.CBOR.encode('options')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })

      // subsequent POST of credential data to server
      } else {
        decodedData = window.CBOR.decode(options.body)
        expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4,5,6]))
        expect(decodedData.attestationObject).toEqual(new Uint8Array([1,2,3]))
        expect(options.headers['X-CSRFToken']).toBe()
        return Promise.resolve({ ok: true })
      }
    })

    button.click()
  })

  test.each([
    ['network'],
    ['server'],
  ])('alerts if fetching WebAuthn options fails (%s error)', (errorType, done) => {
    jest.spyOn(window, 'fetch').mockImplementation((_url, options = {}) => {
      if (errorType == 'network') {
        return Promise.reject('error')
      } else {
        return Promise.resolve({ ok: false, statusText: 'error' })
      }
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      expect(msg).toEqual('Error during registration.\n\nerror')
      done()
    })

    button.click()
  })

  test.each([
    ['network error'],
    ['internal server error'],
    ['bad request'],
  ])('alerts if sending WebAuthn credentials fails (%s)', (errorType, done) => {
    jest.spyOn(window.navigator.credentials, 'create').mockImplementation(() => {
      // fake PublicKeyCredential response from WebAuthn API
      return Promise.resolve({ response: {} })
    })

    jest.spyOn(window, 'fetch').mockImplementation((_url, options = {}) => {
      // initial fetch of options from the server
      if (!options.method) {
        webauthnOptions = window.CBOR.encode('options')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })

      // subsequent POST of credential data to server
      } else {
        switch (errorType) {
          case 'network error':
            return Promise.reject('error')
          case 'bad request':
            message = Promise.resolve(window.CBOR.encode('error'))
            return Promise.resolve({ ok: false, arrayBuffer: () => message })
          case 'internal server error':
            message = Promise.reject('encoding error')
            return Promise.resolve({ ok: false, arrayBuffer: () => message, statusText: 'error' })
        }
      }
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      expect(msg).toEqual('Error during registration.\n\nerror')
      done()
    })

    button.click()
  })

  test('alerts if comms with the authenticator fails', (done) => {
    jest.spyOn(window.navigator.credentials, 'create').mockImplementation(() => {
      return Promise.reject(new DOMException('error'))
    })

    jest.spyOn(window, 'fetch').mockImplementation((_url, options) => {
      // initial fetch of options from the server
      webauthnOptions = window.CBOR.encode('options')

      return Promise.resolve({
        ok: true, arrayBuffer: () => webauthnOptions
      })
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      expect(msg).toEqual('Error during registration.\n\nerror')
      done()
    })

    button.click()
  })
})
