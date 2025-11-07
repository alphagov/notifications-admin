import AuthenticateSecurityKey from '../../app/assets/javascripts/esm/authenticate-security-key.mjs';
import * as helpers from './support/helpers.js';
import { jest } from '@jest/globals';


beforeAll( async() => {
  const CBOR = await import('../../node_modules/cbor-js/cbor.js');
  window.CBOR = CBOR.default || CBOR;
})

describe('Authenticate with security key', () => {
  let button;
  let mockAuthLocation;
  let mockWindowLocation;
  let mockClickEvent;
  let mockFetch;
  let mockWebauthnOptions;
  let mockLoginResponse;
  let authenticateKeyInstance;
  

  const mockBrowserCredentials = {
    get: jest.fn(),
  };

  let credentialsGetResponse = {
    response: {
      authenticatorData: [2, 2, 2],
      signature: [3, 3, 3],
      clientDataJSON: [4, 4, 4]
    },
    rawId: [1, 1, 1],
    type: "public-key",
  };

  beforeAll(() => {
    mockAuthLocation = new helpers.LocationMock('http://localhost:6012/webauth/authenticate');
  });

  afterAll(() => {
    mockAuthLocation.reset();
    jest.restoreAllMocks();
  });

  beforeEach(() => {
    // disable console.error() so we don't see it in test output
    // you might need to comment this out to debug some failures
    console.error = jest.fn();

    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <button data-notify-module="authenticate-security-key" data-module="govuk-button" data-csrf-token="abc123"></button>`;

    button = document.querySelector('[data-notify-module="authenticate-security-key"]');

    // create a mock event for the click handler
    mockClickEvent = { preventDefault: jest.fn() };

    // mock the window fetch function
    mockFetch = jest.fn();
    window.fetch = mockFetch;

    // mock WebAuthn browser API
    window.navigator.credentials = mockBrowserCredentials;

    // mock the window location object
    mockWindowLocation = new helpers.LocationMock();
    window.location = mockWindowLocation;
    mockWindowLocation.assign = jest.fn();

    // mock error banner js
    window.GOVUK.ErrorBanner = {
      showBanner: jest.fn(),
      hideBanner: jest.fn(),
    };

    mockWebauthnOptions = window.CBOR.encode('someArbitraryOptions');
    mockLoginResponse = window.CBOR.encode({ redirect_url: '/foo' });
    // instantiate class
    authenticateKeyInstance = new AuthenticateSecurityKey(button);
  });

  afterEach(() => {
    jest.restoreAllMocks()
    mockFetch.mockClear();
    delete window.fetch;
    delete window.navigator.credentials;
  });

  it('authenticates a credential and redirects based on the admin app response', async () => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });
    
    // mock getCredential response
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockLoginResponse)),
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    const mockFetchOptions = mockFetch.mock.calls[1][1]
    expect(mockFetchOptions.headers).toEqual({ 'X-CSRFToken': 'abc123' });
    expect(mockFetchOptions.method).toBe('POST');

    expect(mockBrowserCredentials.get.mock.calls[0][0]).toEqual('someArbitraryOptions')

    const decodedData = window.CBOR.decode(mockFetchOptions.body)
    expect(decodedData.credentialId).toEqual(new Uint8Array([1, 1, 1]))
    expect(decodedData.authenticatorData).toEqual(new Uint8Array([2, 2, 2]))
    expect(decodedData.signature).toEqual(new Uint8Array([3, 3, 3]))
    expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4, 4, 4]))
 
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockWindowLocation.assign).toHaveBeenCalledWith('/foo');
    expect(window.GOVUK.ErrorBanner.showBanner).not.toHaveBeenCalled();
  });

  it('authenticates and passes a redirect url through to the authenticate admin endpoint', async() => {
    window.location.search = '?next=%2Ffoo%3Fbar%3Dbaz';

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock getCredential response
    credentialsGetResponse = {
        response: {
          authenticatorData: [],
          signature: [],
          clientDataJSON: []
        },
        rawId: [],
        type: "public-key",
    };
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockLoginResponse)),
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockBrowserCredentials.get.mock.calls[0][0]).toEqual('someArbitraryOptions');
    expect(mockWindowLocation.assign).toHaveBeenCalledWith('/foo');
    expect(window.GOVUK.ErrorBanner.showBanner).not.toHaveBeenCalled();
    expect(mockFetch.mock.calls[1][0].toString()).toEqual(
      'https://www.notifications.service.gov.uk/webauthn/authenticate?next=%2Ffoo%3Fbar%3Dbaz'
    );
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn fails (%s error)', async(errorType) => {

    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'error'
      });
    }

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockWindowLocation.assign).not.toHaveBeenCalled();
    expect(window.GOVUK.ErrorBanner.showBanner).toHaveBeenCalled();
  });

  it('errors if comms with the authenticator fails', async() => {
    
    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock getCredential response
    mockBrowserCredentials.get.mockResolvedValueOnce(new DOMException('error'));

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(window.GOVUK.ErrorBanner.showBanner).toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if POSTing WebAuthn credentials fails (%s)', async(errorType) => {
     
    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock getCredential response
    if (errorType == 'network') {
      mockBrowserCredentials.get.mockRejectedValueOnce('error');
    } else {
      mockBrowserCredentials.get.mockResolvedValueOnce({ ok: false, statusText: 'FORBIDDEN' });
    }

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockBrowserCredentials.get.mock.calls[0][0]).toEqual('someArbitraryOptions');
    expect(mockWindowLocation.assign).not.toHaveBeenCalled();
    expect(window.GOVUK.ErrorBanner.showBanner).toHaveBeenCalled();
  });

  it('reloads page if POSTing WebAuthn credentials returns 403', async() => {

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock getCredential
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock postCredential fail
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockBrowserCredentials.get.mock.calls[0][0]).toEqual('someArbitraryOptions');
    expect(mockWindowLocation.assign).not.toHaveBeenCalledWith();
    expect(window.GOVUK.ErrorBanner.showBanner).toHaveBeenCalled();
  });
});
