beforeAll(() => {
  window.CBOR = require('../../node_modules/cbor-js/cbor.js')
  require('../../app/assets/javascripts/authenticateSecurityKey.js')

  // populate missing values to allow consistent jest.spyOn()
  window.fetch = () => { }
  window.navigator.credentials = { get: () => { } }
  window.GOVUK.ErrorBanner = {
    showBanner: () => {},
    hideBanner: () => {}
  };
})

afterAll(() => {
  require('./support/teardown.js')

  // restore window attributes to their original undefined state
  delete window.fetch
  delete window.navigator.credentials
})

describe('Authenticate with security key', () => {
  let button

  beforeEach(() => {
    // disable console.error() so we don't see it in test output
    // you might need to comment this out to debug some failures
    jest.spyOn(console, 'error').mockImplementation(() => {})

    document.body.innerHTML = `
      <button type="submit" data-module="authenticate-security-key" data-csrf-token="abc123"></button>`

    button = document.querySelector('[data-module="authenticate-security-key"]')
    window.GOVUK.modules.start()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('authenticates a credential and redirects based on the admin app response', (done) => {

    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((_url) => {
        // initial fetch of options from the server
        // fetch defaults to GET
        // options from the server are CBOR-encoded
        const webauthnOptions = window.CBOR.encode('someArbitraryOptions')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })
      })

    jest.spyOn(window.navigator.credentials, 'get').mockImplementation((options) => {
      expect(options).toEqual('someArbitraryOptions')

      // fake PublicKeyCredential response from WebAuthn API
      // all of the array properties represent Array(Buffer) objects
      const credentialsGetResponse = {
        response: {
          authenticatorData: [2, 2, 2],
          signature: [3, 3, 3],
          clientDataJSON: [4, 4, 4]
        },
        rawId: [1, 1, 1],
        type: "public-key",
      }
      return Promise.resolve(credentialsGetResponse)
    })

    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((_url, options = {}) => {
        // subsequent POST of credential data to server
        const decodedData = window.CBOR.decode(options.body)
        expect(decodedData.credentialId).toEqual(new Uint8Array([1, 1, 1]))
        expect(decodedData.authenticatorData).toEqual(new Uint8Array([2, 2, 2]))
        expect(decodedData.signature).toEqual(new Uint8Array([3, 3, 3]))
        expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4, 4, 4]))
        expect(options.headers['X-CSRFToken']).toBe('abc123')
        const loginResponse = window.CBOR.encode({ redirect_url: '/foo' })

        return Promise.resolve({
          ok: true, arrayBuffer: () => Promise.resolve(loginResponse)
        })
      })

    jest.spyOn(window.location, 'assign').mockImplementation((href) => {
      expect(href).toEqual("/foo")
      done()
    })

    // this will make the test fail if the error banner is displayed
    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done('didnt expect the banner to be shown')
    })

    button.click()
  })

  test('authenticates and passes a redirect url through to the authenticate admin endpoint', (done) => {
    // https://github.com/facebook/jest/issues/890#issuecomment-415202799
    window.history.pushState({}, 'Test Title', '/?next=%2Ffoo%3Fbar%3Dbaz')

    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((_url) => {
        // initial fetch of options from the server
        // fetch defaults to GET
        // options from the server are CBOR-encoded
        let webauthnOptions = window.CBOR.encode('someArbitraryOptions')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })
      })

    jest.spyOn(window.navigator.credentials, 'get').mockImplementation((options) => {
      let credentialsGetResponse = {
        response: {
          authenticatorData: [],
          signature: [],
          clientDataJSON: []
        },
        rawId: [],
        type: "public-key",
      }
      return Promise.resolve(credentialsGetResponse)
    })

    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((url, options = {}) => {
        // subsequent POST of credential data to server
        expect(url.toString()).toEqual(
          'https://www.notifications.service.gov.uk/webauthn/authenticate?next=%2Ffoo%3Fbar%3Dbaz'
        )
        return Promise.resolve({
          ok: true, arrayBuffer: () => Promise.resolve(window.CBOR.encode({ redirect_url: '/foo' }))
        })
      })

    jest.spyOn(window.location, 'assign').mockImplementation((href) => {
      // ensure that the fetch mock implementation above was called
      expect.assertions(1)
      done()
    })

    button.click()
  })

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn fails (%s error)', (errorType, done) => {
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

  test('errors if comms with the authenticator fails', (done) => {
    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((_url) => {
        const webauthnOptions = window.CBOR.encode('someArbitraryOptions')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })
      })

    jest.spyOn(window.navigator.credentials, 'get').mockImplementation(() => {
      return Promise.reject(new DOMException('error'))
    })

    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation(() => {
      done()
    })

    button.click()
  })

  test.each([
    ['network'],
    ['server'],
  ])('errors if POSTing WebAuthn credentials fails (%s)', (errorType, done) => {
    jest.spyOn(window, 'fetch')
      .mockImplementationOnce((_url) => {
        const webauthnOptions = window.CBOR.encode('someArbitraryOptions')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })
      })

    jest.spyOn(window.navigator.credentials, 'get').mockImplementation((options) => {
      expect(options).toEqual('someArbitraryOptions')
      const credentialsGetResponse = {
        response: {
          authenticatorData: [2, 2, 2],
          signature: [3, 3, 3],
          clientDataJSON: [4, 4, 4]
        },
        rawId: [1, 1, 1],
        type: "public-key",
      }
      return Promise.resolve(credentialsGetResponse)
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


  test('reloads page if POSTing WebAuthn credentials returns 403', (done) => {
    jest.spyOn(window, 'fetch').mockImplementationOnce((_url) => {
      const webauthnOptions = window.CBOR.encode('someArbitraryOptions')

        return Promise.resolve({
          ok: true, arrayBuffer: () => webauthnOptions
        })
      })

    jest.spyOn(window.navigator.credentials, 'get').mockImplementation((options) => {
      expect(options).toEqual('someArbitraryOptions')
      const credentialsGetResponse = {
        response: {
          authenticatorData: [2, 2, 2],
          signature: [3, 3, 3],
          clientDataJSON: [4, 4, 4]
        },
        rawId: [1, 1, 1],
        type: "public-key",
      }
      return Promise.resolve(credentialsGetResponse)
    })

    jest.spyOn(window, 'fetch').mockImplementationOnce((_url) => {
      return Promise.resolve(
        {
          ok: false,
          status: 403,
        })
    })

    // assert that reload is called and the page is refreshed
    jest.spyOn(window.location, 'reload').mockImplementation(() => {
      done()
    })

    // this will make the test fail if the error banner is displayed
    jest.spyOn(window.GOVUK.ErrorBanner, 'showBanner').mockImplementation((msg) => {
      done(msg)
    })

    button.click()
  })


})
