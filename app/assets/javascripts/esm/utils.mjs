// Taken from https://youmightnotneedjquery.com/#offset
const offset = (el) => {
  const box = el.getBoundingClientRect();
  const docElem = document.documentElement;
  
  return {
    top: box.top + window.scrollY - docElem.clientTop,
    left: box.left + window.scrollX - docElem.clientLeft
  };
};

export { offset };
