import { isSupported } from 'govuk-frontend';
import morphdom from 'morphdom';
import { locationReload } from '../utils/location.mjs';

const resourceState = {};
const defaultInterval = 2000;

// Keyed by resource URL. Each entry holds:
// renderers – Set of renderer functions registered by all instances
// timeout – The single active setTimeout handle
// interval – Current backoff interval
// fetching – Whether a fetch is in flight
function getState(resource) {
  if (!resourceState[resource]) {
    resourceState[resource] = {
      renderers: new Set(),
      timeout: null,
      interval: defaultInterval,
      fetching: false,
    };
  }
  return resourceState[resource];
}

// Because the polling loop is shared, it can't belong to one instance. 
// It reads and writes resourceState[resource] directly. 
// All instances for the same URL share the exact same timeout and interval.
async function pollResource(resource, $form) {
  const state = getState(resource);

  clearTimeout(state.timeout);

  if (document.visibilityState === 'hidden' || state.fetching) {
    state.timeout = setTimeout(() => pollResource(resource, $form), state.interval);
    return;
  }

  state.fetching = true;
  const startTime = Date.now();

  const method = $form ? 'POST' : 'GET';
  const fetchOptions = { method, headers: {} };

  if ($form) {
    const formEl = document.getElementById($form);
    if (formEl) {
      fetchOptions.body = new URLSearchParams(new FormData(formEl)).toString();
      fetchOptions.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }
  }

  try {
    const response = await fetch(resource, fetchOptions);

    if (!response.ok) {
      if (response.status === 401) {
        locationReload();
      }
      state.fetching = false;
      return;
    }

    const responseData = await response.json();

    for (const renderer of state.renderers) {
      renderer(responseData);
    }

    if (responseData.stop === 1) {
      state.fetching = false;
      return;
    }

    // Calculate backoff from actual response time, replacing the initial default.
    state.interval = UpdateContent.prototype.calculateBackoff(Date.now() - startTime);

  } catch {
    // Network error – back off and retry.
  }

  state.fetching = false;
  state.timeout = setTimeout(() => pollResource(resource, $form), state.interval);
}

class UpdateContent {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    
    this.$contents = $module.firstElementChild;
    this.key = $module.dataset.key;
    this.resource = $module.dataset.resource;
    this.$form = $module.dataset.form;

    // Replace component with contents.
    // The renderer does this anyway when diffing against the first response
    $module.parentNode.replaceChild(this.$contents, $module);

    const state = getState(this.resource);
    const renderer = this.getRenderer(this.$contents, this.key);

    state.renderers.add(renderer);

    if (state.renderers.size === 1) {
      state.timeout = setTimeout(() => pollResource(this.resource, this.$form), state.interval);
    }
  }

  calculateBackoff(responseTime) {
    return Math.max(Math.floor(250 * Math.sqrt(responseTime)) - 1000, 1000);
  }

  getRenderer(contents, key) {
    return (response) => {
      if (!response || !response[key]) return;

      let contentHasUpdated = false;
      const parser = new DOMParser();
      const doc = parser.parseFromString(response[key], 'text/html');
      const newContents = doc.body.firstElementChild;

      morphdom(contents, newContents, {
        onBeforeElUpdated: (fromEl, toEl) => {
          // spec - https://dom.spec.whatwg.org/#concept-node-equals
          if (fromEl.isEqualNode(toEl)) {
            return false;
          } else if (fromEl === contents) { // if root node is different, updates will apply
            contentHasUpdated = true;
          }
          return true;
        }
      });

      if (contentHasUpdated) {
        document.dispatchEvent(new CustomEvent('updateContent.onafterupdate', {
          detail: { el: [contents] }
        }));
      }
    };
  }
}

export default UpdateContent;
