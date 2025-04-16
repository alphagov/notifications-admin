import CheckReportStatus from '../../app/assets/javascripts/esm/check-report-status.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers';

const requestID = '999999f-0cad-491f-bec8-ab999999eaf';
const route = `/services/6658542f-0cad-491f-bec8-ab8457700ead/download-report/${requestID}`;

let responseObj = {};
let locationMock;

beforeAll(() => {
  jest.useFakeTimers();
  // JDSOM does no have fetch
  global.fetch = jest.fn().mockImplementation(() =>
    Promise.resolve({
      json: () => Promise.resolve(responseObj),
    })
  );
  jest.spyOn(global, 'fetch');
  // mock calls to window.location
  locationMock = new helpers.LocationMock();
  window.location.pathname = route;
});

afterAll(() => {
  jest.restoreAllMocks();
  locationMock.reset();
  delete global.fetch;
});

describe('Update content', () => {

  beforeEach(() => {
    document.body.classList.add('govuk-frontend-supported')
    document.body.innerHTML = `
      <div role="status" data-notify-module="check-report-status">
        <p class="govuk-body">We are creating a CSV file of of fake notifications.</p>
      </div>
    `;

  });

  afterEach(() => {

    document.body.innerHTML = '';

    // ensure any timers set by continually starting the module are cleared
    jest.clearAllTimers();

  });

  test('it should fetch data from the endpoint', async () => {
    responseObj = {status: 'pending'}
    new CheckReportStatus('[data-notify-module="check-report-status"]');

    expect(global.fetch).toHaveBeenCalledWith(
      `${route}/status.json`,
    );
  });


  test.only('it should keep checking every 20s if the status is still not "stored', async () => {
    responseObj = {status: 'pending'}
    new CheckReportStatus('[data-notify-module="check-report-status"]');

    expect(global.fetch).toHaveBeenCalledTimes(1);
    jest.advanceTimersByTime(20001);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    jest.advanceTimersByTime(20001);
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });


  test('it should update page text if status of the report is "stored"', async () => {

    responseObj = {status: 'stored'}

    new CheckReportStatus('[data-notify-module="check-report-status"]');

    // jest.advanceTimersByTime(500);

    expect(document.body.textContent.trim()).toContain("0")
     
  });

});
