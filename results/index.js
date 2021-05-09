const pageArguments = new URLSearchParams(window.location.search);
const referenceId = pageArguments.get(`reference`);
const compareId = pageArguments.get(`compare`);

// Fetch the diff list for this comparison
(async function () {
  const data = await fetch(`./${compareId}/diffs.json`).then((r) => r.json());
  Object.entries(data).forEach(processDiffs);
})();

function processDiffs([browserWidth, difflist]) {
  const imageSets = difflist.map((diff) => buildImage(browserWidth, diff));
  imageSets.forEach(processImageSet);
}

function processImageSet(set) {
  const section = document.createElement(`section`);
  section.innerHTML = `
    <h2>${set.diff}</h2>
  `;
  section.append(set.original);
  section.append(set.compare);
  reference.append(section);
}

function buildImage(browserWidth, diff) {
  const original = `./${referenceId}/${browserWidth}/${diff}/screenshot.png`;
  const diffBase = `./${compareId}/${browserWidth}/${diff}`;
  const compare = `${diffBase}/screenshot.png`;
  const originalMask = `${diffBase}/original_mask.png`;
  const diffMask = `${diffBase}/diff_mask.png`;

  return {
    diff: diff,
    original: buildImageElement(original, originalMask),
    compare: buildImageElement(compare, diffMask),
  };
}

function buildImageElement(screenshot, overlay, height = 500) {
  const figure = document.createElement(`figure`);
  figure.setAttribute(`style`, `
    background-image: url("${screenshot}");
    height: ${height}px;
  `);

  const img = new Image();
  img.src = overlay;
  img.height = height;
  figure.append(img);
  return figure;
}
