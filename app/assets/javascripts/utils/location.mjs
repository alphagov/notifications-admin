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
  locationReplace
};