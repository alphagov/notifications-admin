import { jest } from '@jest/globals';

// register the mock with the ESM loader first.
jest.unstable_mockModule('../../app/assets/javascripts/utils/location.mjs', () => ({
  locationReplace: jest.fn()
}));

let CheckReportStatus;
let locationReplace;

beforeAll( async() => {
  const checkReportStatusModule = await import('../../app/assets/javascripts/esm/check-report-status.mjs');
  const locationUtilModule = await import('../../app/assets/javascripts/utils/location.mjs');

  CheckReportStatus = checkReportStatusModule.default;
  locationReplace = locationUtilModule.locationReplace;
})

describe('CheckReportStatus', () => {
  let $module;
  let mockFetch;
  let checkReportStatus;
  const route = `/services/serviceID/download-report/requestID`;

  beforeAll(() => {
    jest.useFakeTimers();
  });

  beforeEach(() => {
    jest.spyOn(global, 'setTimeout');
    // Create a mock module element
    document.body.classList.add('govuk-frontend-supported')
    document.body.innerHTML = `
      <div role="status" data-notify-module="check-report-status">
        <p class="govuk-body">We are creating a CSV file of of fake notifications.</p>
      </div>
    `;
    $module = document.querySelector('[data-notify-module="check-report-status"]');

    // Mock the window fetch function
    mockFetch = jest.fn();
    window.fetch = mockFetch;

    // Set the JSDOM URL path
    window.history.replaceState({}, '', route);

    // Spy on console.error
    console.error = jest.fn();

    // Instantiate the class
    checkReportStatus = new CheckReportStatus($module);
  });

  afterEach(() => {
    // Clean up the mock module and restore the original functions
    document.body.removeChild($module);
    jest.restoreAllMocks();
  });

  describe('checkStatus', () => {
    it('should call fetch with the correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'stored' })
      });
      await checkReportStatus.checkStatus();
      expect(mockFetch).toHaveBeenCalledWith(`${route}/status.json`);
    });

    it('should throw an error if the request fetch initiated fails', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Fetch error'));
      await checkReportStatus.checkStatus();
      expect(console.error).toHaveBeenCalledWith('Error checking report status:', new Error('Fetch error'));
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), checkReportStatus.fetchInterval);
    });

    it('should poll the endpoint with the specified delay while the download is pending', async () => {
      jest.spyOn(checkReportStatus, 'checkStatus');
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'pending' }),
      });
      expect(checkReportStatus.checkStatus).toHaveBeenCalledTimes(0);
      await checkReportStatus.checkStatus();
      jest.advanceTimersByTime(checkReportStatus.fetchInterval + 1);
      await checkReportStatus.currentCheck;
      mockFetch.mockResolvedValue({
        json: () => Promise.resolve({ status: 'stored', ok: true }),
      });
      jest.advanceTimersByTime(checkReportStatus.fetchInterval + 1);
      expect(checkReportStatus.checkStatus).toHaveBeenCalledTimes(3);
    });

    describe.each(['stored', 'failed'])("if the download status is '%s'", (status) => {
      beforeEach(async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ status: status }),
        });
        await checkReportStatus.checkStatus();
        locationReplace.mockClear();
      });

      it('should update the page to prep the user for a redirect', () => {
        expect($module.innerHTML).toBe('<p class="govuk-body">Report status has been updated. We will redirect you shortly.</p>');
      });

      it('should redirect after the specified delay', () => {
        expect(locationReplace).not.toHaveBeenCalled();
        expect(setTimeout.mock.lastCall[1]).toEqual(checkReportStatus.redirectDelay);
        jest.advanceTimersByTime(checkReportStatus.redirectDelay + 1);
        expect(locationReplace).toHaveBeenCalledWith(route);
      });
    });
  });
});
