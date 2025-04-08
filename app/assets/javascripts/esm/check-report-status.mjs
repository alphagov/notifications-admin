import { isSupported } from 'govuk-frontend';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class CheckReportStatus {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.$component = $module;

    const pollingInterval = 5000; // 5 seconds in milliseconds
const maxPollingDuration = 30000; // 300 seconds (5 minutes) in milliseconds
const apiEndpoint = '/services/af41756e-5f17-4e4d-ac98-bea1bc8fe366/download-report/39acaf48-0cd4-4548-9783-0597081c8ac6/status.json'; // Replace with your API endpoint
const successResponse = 'success'; // Define what constitutes a success response

async function pollApi(apiEndpoint, successResponse, pollingInterval, maxPollingDuration) {
  const startTime = Date.now(); // Record the start time

  const makeRequest = async () => {
      try {
          const response = await fetch(apiEndpoint); // Make request
          const data = await response.json();

          if (data.status === successResponse) {
              console.log('Success response received:', data);
              return; // // Stop polling if success response
          }

          const elapsedTime = Date.now() - startTime;

          if (elapsedTime < maxPollingDuration) {
              setTimeout(makeRequest, pollingInterval); // Schedule next request
          } else {
              console.log('Maximum polling duration reached. Stopping polling.');
          }
      } catch (error) {
          console.error('Error making API request:', error);
          const elapsedTime = Date.now() - startTime;

          if (elapsedTime < maxPollingDuration) {
              setTimeout(makeRequest, pollingInterval); // Schedule next request
          } else {
              console.log('Maximum polling duration reached. Stopping polling.');
          }
      }
  };

  makeRequest(); // Start the first request
}

pollApi(apiEndpoint, successResponse, pollingInterval, maxPollingDuration);
  }
}