import { isSupported } from 'govuk-frontend';

class Homepage {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }

    let iterations = 0;
    let timeout = null;

    $module.addEventListener("click", () => {
      if (++iterations == 5) {
        $module.classList.toggle('product-page-intro-wrapper--alternative');
      }
      clearTimeout(timeout);
      timeout = setTimeout(() => iterations = 0, 1500);
    });
  }
}

export default Homepage;
