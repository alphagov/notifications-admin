import { isSupported } from 'govuk-frontend';
import morphdom from 'morphdom';

const queues = {};
const timeouts = {};
const defaultInterval = 2000;
const intervals = {};

class UpdateContent {

  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    this.$contents = $module.firstElementChild;
    this.key = $module.dataset.key;
    this.resource = $module.dataset.resource;
    this.$form = $module.dataset.form;

    intervals[this.resource] = defaultInterval;

    // Replace component with contents.
    // The renderer does this anyway when diffing against the first response
    $module.parentNode.replaceChild(this.$contents, $module);

    const initialBoundPoll = this.poll.bind(this,
      this.getRenderer(this.$contents, this.key),
      this.resource,
      this.getQueue(this.resource),
      this.$form
    );

    timeouts[this.resource] = setTimeout(
      initialBoundPoll,
      intervals[this.resource]
    );
  }

  calculateBackoff(responseTime) {
    return parseInt(Math.max(
      (250 * Math.sqrt(responseTime)) - 1000,
      1000
    ));
  }

  getQueue(resource) {
    return (queues[resource] = queues[resource] || []);
  }

  flushQueue(queue, response) {
    while (queue.length) queue.shift()(response);
  }

  clearQueue(queue) {
    queue.length = 0;
  }

  getRenderer(contents, key) {
    const result = response => {
      let contentHasUpdated = false;

      // HTML node from string
      const parser = new DOMParser();
      const doc = parser.parseFromString(response[key], 'text/html');
      const newContents = doc.body.firstElementChild;

      morphdom(
        contents,
        newContents,
        {
          onBeforeElUpdated: function (fromEl, toEl) {
            // spec - https://dom.spec.whatwg.org/#concept-node-equals
            if (fromEl.isEqualNode(toEl)) {
              return false;
            } else if (fromEl === contents) { // if root node is different, updates will apply
              contentHasUpdated = true;
            }
            return true;
          }
        }
      );

      console.log(`[Renderer for ${key}]  contentHasUpdated: ${contentHasUpdated ? 'true': 'false'}`);

      if (contentHasUpdated === true) {
        const event = new CustomEvent("updateContent.onafterupdate", { detail: { el: [contents]} });
        document.dispatchEvent(event);
      }
    };

    result.id = `${key}_renderer`;

    return result;
  }

  async poll(renderer, resource, queue, form) {
    const startTime = Date.now();

    console.log(`[Poll function:start]  resource is ${resource} renderer is ${renderer.id}  queue length is ${queue.length}`);

    const boundPoll = this.poll.bind(this, renderer, resource, queue, form);
    
    clearTimeout( timeouts[resource]);

    timeouts[resource] = setTimeout(
      boundPoll,
      intervals[resource]
    );

    // Only send requests when window/tab is in use and nothing in queue
    if (document.visibilityState !== "hidden") {
      if (queue.push(renderer) === 1) {
        const method = form ? 'POST' : 'GET';
        let fetchOptions = { method: method, headers: {} };

        if (form) {
          fetchOptions.body = new URLSearchParams(new FormData(document.getElementById(form))).toString();
          fetchOptions.headers['Content-Type'] = 'application/x-www-form-urlencoded';
        }

        try {
          console.log(`[Poll function:pre-fetch]  resource is ${resource} renderer is ${renderer.id}`);
          const response = await fetch(resource, fetchOptions);
          console.log(`[Poll function:post-fetch] resource is ${resource} renderer is ${renderer.id}  response.ok is ${response.ok ? 'true' : 'false'}`)
      
          if (!response.ok) {
            if (response.status === 401) {
              window.location.reload();
            }
            clearTimeout(timeouts[resource]);
            this.clearQueue(queue);
            return;
          }

          const responseData = await response.json();
          console.log(`[Poll function:data-parsed]  resource is ${resource} renderer is ${renderer.id}`);
          this.flushQueue(queue, responseData);

          if (responseData.stop === 1) {
            clearTimeout(timeouts[resource]); // stop polling
            return;
          }
          
          intervals[resource] = this.calculateBackoff(Date.now() - startTime); // keep polling but adjust for response time

        } catch (error) {
          console.log(`[Poll function:catch]  resource is ${resource} renderer is ${renderer.id}, error.message is ${error.message}`);
          clearTimeout(timeouts[resource]); // stop polling
          this.clearQueue(queue);
          return;
        }
      }
    }

  }
}

export default UpdateContent;