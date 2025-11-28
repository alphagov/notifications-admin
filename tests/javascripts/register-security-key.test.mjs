import RegisterSecurityKey from '../../app/assets/javascripts/esm/register-security-key.mjs';
import ErrorBanner from '../../app/assets/javascripts/esm/error-banner.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers';

beforeAll( async() => {
  const CBOR = await import('../../node_modules/cbor-js/cbor.js');
  window.CBOR = CBOR.default || CBOR;
})

describe('Register security key', () => {
  let button;
  let mockAuthLocation;
  let mockWindowLocation;
  let mockClickEvent;
  let mockFetch;
  let mockWebauthnOptions;
  let registerKeyInstance;
  let errorBannerShowBannerSpy;

  const mockBrowserCredentials = {
    create: jest.fn(),
  };

  let credentialsGetResponse = {
    response: {
      attestationObject: [1, 2, 3],
      clientDataJSON: [4, 5, 6],
    }
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
      <button href="#" class="govuk-button govuk-button--secondary" data-notify-module="register-security-key" data-module="govuk-button">
        Register a key
      </button>`;

    button = document.querySelector('[data-notify-module="register-security-key"]');
    // create a mock event for the click handler
    mockClickEvent = { preventDefault: jest.fn() };

    // spy on the showBanner method of ErroBanner class
    // and mock its implementation, allowing us to assert whether it was called
    errorBannerShowBannerSpy = jest.spyOn(ErrorBanner.prototype, 'showBanner').mockImplementation(() => {});

    // mock the window fetch function
    mockFetch = jest.fn();
    window.fetch = mockFetch;

    // mock WebAuthn browser API
    window.navigator.credentials = mockBrowserCredentials;

    // mock the window location object
    mockWindowLocation = new helpers.LocationMock();
    window.location = mockWindowLocation;
    mockWindowLocation.reload = jest.fn();

    mockWebauthnOptions = window.CBOR.encode('options');
    // instantiate class
    registerKeyInstance = new RegisterSecurityKey(button);
  })

  afterEach(() => {
    jest.restoreAllMocks();
    jest.resetModules();
    mockFetch.mockClear();
    delete window.fetch;
    delete window.navigator.credentials;
  });

  it('creates a new credential and reloads', async() => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce(credentialsGetResponse);

    // mock postCredential
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve({ ok: true }))
    });

    await registerKeyInstance.registerKey(mockClickEvent);

    const mockFetchOptions = mockFetch.mock.calls[1][1];
    expect(mockFetchOptions.headers['X-CSRFToken']).toBe();
    expect(mockFetchOptions.method).toBe('POST');

    const decodedData = window.CBOR.decode(mockFetchOptions.body);
    expect(decodedData.attestationObject).toEqual(new Uint8Array([1, 2, 3]));
    expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4, 5, 6]));
 
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockWindowLocation.reload).toHaveBeenCalledWith();
    expect(ErrorBanner.prototype.showBanner).not.toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn options fails (%s error)', async(errorType) => {
    
    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'error'
      });
    }

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockWindowLocation.reload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if sending WebAuthn credentials fails (%s)', async(errorType) => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce({response: {}});

    // mock postCredential
    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'FORBIDDEN'
      });
    }

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockWindowLocation.reload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  it('errors if comms with the authenticator fails', async() => {
  
    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: jest.fn(() => Promise.resolve(mockWebauthnOptions)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce(new DOMException('error'));

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockWindowLocation.reload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  })
});
