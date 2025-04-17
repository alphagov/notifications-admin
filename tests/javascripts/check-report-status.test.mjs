import CheckReportStatus from '../../app/assets/javascripts/esm/check-report-status.mjs';
import { jest } from '@jest/globals';
import * as helpers from './support/helpers';

const requestID = '999999f-0cad-491f-bec8-ab999999eaf';
const route = `/services/6658542f-0cad-491f-bec8-ab8457700ead/download-report/${requestID}`;

let responseObj = {};
let locationMock;

jest.useFakeTimers();

beforeAll(() => {
  // JDSOM does no have fetch
  window.fetch = jest.fn();
  // window.fetch.mockImplementation(() => {
  //   console.log('before mock fetch promise return');
  //    return Promise.resolve({
  //       'json': () => Promise.resolve(responseObj)
  //     })
  // });
  // window.fetch = jest.fn().mockImplementation(() =>
  //   Promise.resolve({
  //     json: () => Promise.resolve(responseObj),
  //   })
  // );
  // jest.spyOn(global, 'fetch');
  // mock calls to window.location
  locationMock = new helpers.LocationMock();
  window.location.pathname = route;
});

afterAll(() => {
  jest.restoreAllMocks();
});

describe('CheckReportStatus', () => {

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
    jest.clearAllTimers()
    window.fetch = undefined;
    locationMock.reset();
  });

  test('it should fetch data from the endpoint', async () => {
    responseObj = {status: 'pending'}
    new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));

    expect(global.fetch).toHaveBeenCalledWith(
      `${route}/status.json`,
    );
  });


  test.only('it should keep checking every 20s if the status is still not "stored', async () => {

    responseObj = {status: 'pending'}
    jest.spyOn(window, 'fetch').mockImplementationOnce(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
      jest.advanceTimersByTime(20001);
      expect(global.fetch).toHaveBeenCalledTimes(2);
      jest.advanceTimersByTime(20001);
      expect(global.fetch).toHaveBeenCalledTimes(3);
      return Promise.resolve({
        json: () => Promise.resolve(responseObj)
      })
    })

    new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));

    // debugger;
    // new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));
    // console.log(performance.now(), 'before')
    // expect(global.fetch).toHaveBeenCalledTimes(1);
    // jest.advanceTimersByTime(20001);
    // console.log(performance.now(), 'after')
    
    // expect(global.fetch).toHaveBeenCalledTimes(2);
    // jest.advanceTimersByTime(20001);
    // expect(global.fetch).toHaveBeenCalledTimes(3);
  });


  test('it should update page text if status of the report is "stored"', async () => {
    responseObj = {status: 'stored'}

    jest.spyOn(window, 'fetch').mockImplementationOnce(() => {
      new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));
      expect(document.body.textContent.trim()).toContain('Report status has been updated. We will redirect you shortly.')

      return Promise.resolve({
        json: () => Promise.resolve(responseObj)
      })
    })

    // new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));
    // console.log(performance.now(), 'before')
    // jest.advanceTimersByTime(500);
    // console.log(performance.now(), 'after')
    // expect(document.body.textContent.trim()).toContain('Report status has been updated. We will redirect you shortly.')
  });

  test('it should reload the page after 10s if status is no longer "pending"', async () => {

    responseObj = {status: 'failed'};

    window.location.replace = jest.fn();

    new CheckReportStatus(document.querySelector('[data-notify-module="check-report-status"]'));
    
    jest.advanceTimersByTime(10001);

    jest.spyOn(window, 'fetch').mockImplementation(() => {
      expect(window.location.new).toHaveBeenCalled();
    })
  });

});
