const helpers = require('./support/helpers');
beforeAll(() => {
  helpers.setCookie('_ga', 'GA1.1.123.123', { 'days': 365, 'domain': '.notifications.service.gov.uk' });
  helpers.setCookie('_gid', 'GA1.1.456.456', { 'days': 1, 'domain': '.notifications.service.gov.uk' });
  helpers.setCookie('cookies_policy', '{ "analytics": true }', { 'days': 365 });
  helpers.setCookie('random cookie', 'random data', { 'days': 365 });
  require('../../app/assets/javascripts/cookieCleanup.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Cookie cleanup function', () => {
  test("Should delete GA cookies if they exist", () => {
    expect(helpers.getCookie('_ga')).toBeNull();
    expect(helpers.getCookie('_gid')).toBeNull();
  });
  test("Should delete cookies_policy cookie if it exist", () => {
    expect(helpers.getCookie('cookies_policy')).toBeNull();
  });
  test("Should not delete other cookies that are not 'cookies_policy' cookie or GA", () => {
    expect(helpers.getCookie('random cookie')).not.toBeNull();
  });
});