// Taken from https://youmightnotneedjquery.com/#offset
const offset = (el) => {
  const box = el.getBoundingClientRect();
  const docElem = document.documentElement;
  
  return {
    top: box.top + window.scrollY - docElem.clientTop,
    left: box.left + window.scrollX - docElem.clientLeft
  };
};

// Location helpers
const locationReload = () => {
  window.location.reload();
};

const locationReplace = (pathName) => {
  window.location.replace(pathName);
};

const locationAssign = (pathName) => {
  window.location.assign(pathName);
};

export { 
  locationAssign,
  locationReload,
  locationReplace,
  offset,
};
