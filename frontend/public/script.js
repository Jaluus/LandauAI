const waitForElement = (parent, selector) => {
  return new Promise((resolve) => {
    if (parent.querySelector(selector)) {
      return resolve(parent.querySelector(selector));
    }

    const observer = new MutationObserver((mutations) => {
      if (parent.querySelector(selector)) {
        observer.disconnect();
        resolve(parent.querySelector(selector));
      }
    });

    // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
    observer.observe(parent, {
      childList: true,
      subtree: true,
    });
  });
};

const addWatermarkListener = (parent, class_name) => {
  waitForElement(parent, class_name).then((watermark_elem) => {
    watermark_elem.classList.remove("watermark");
    watermark_elem.classList.add("landau-notice");
    watermark_elem.innerHTML =
      "<span style='color: gray; padding: 0px;padding-left: 10px;padding-right: 10px; text-align: center; display: block;'><span style='background: -webkit-linear-gradient(217deg, #ff8f38, #ff3845);-webkit-background-clip: text;-webkit-text-fill-color: transparent;'>Landau</span> macht machmal Fehler. Vorallem beim Rechnen!</span>";
    addWatermarkListener(parent, class_name);
  });
};

addWatermarkListener(document, ".watermark");
