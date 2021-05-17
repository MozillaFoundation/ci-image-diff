const pageArguments = new URLSearchParams(window.location.search);
const referenceId = pageArguments.get(`reference`);
const compareId = pageArguments.get(`compare`);
const create = document.createElement.bind(document);

// Fetch the diff list for this comparison
(async function () {
  const data = await fetch(`./${compareId}/diffs.json`).then((r) => r.json());
  Object.entries(data).forEach(processDiffs);
})();

/**
 * ... docs go here...
 */
function processDiffs([browserWidth, difflist]) {
  const count = difflist.length;

  if (!count) return;

  const option = create(`option`);
  option.value = browserWidth;
  option.textContent = browserWidth;
  diffsets.append(option);

  const [browser, width] = browserWidth.split('-');

  const showOrNot = create(`div`);
  showOrNot.classList.add(`show-or-not`);
  diffs.append(showOrNot);

  const toggle = create(`input`);
  toggle.type = `checkbox`;
  toggle.setAttribute(`checked`, `checked`)
  toggle.id = browserWidth;
  toggle.addEventListener(`change`, evt => {
    const action = evt.target.checked ? `remove` : `add`;
    section.classList[action](`hidden`);
  });
  showOrNot.append(toggle);

  const label = create(`label`);
  label.setAttribute(`for`, browserWidth);
  label.textContent = `${browser} - ${width}px (${count} diff${count>1 ? `s` : ``})`
  showOrNot.append(label);

  const section = create(`section`);
  diffs.append(section);

  const imageSets = difflist.map((diff) => buildImage(browserWidth, diff));
  imageSets.forEach(set => processImageSet(section, set));
}

/**
 * ... docs go here...
 */
function processImageSet(section, set) {
  const specificDiff = create(`section`);
  specificDiff.classList.add(`specific-diff`);
  specificDiff.innerHTML = `
    <h2>Diff for URL: ${set.diff}</h2>
  `;
  const figureSet = create(`div`);
  figureSet.classList.add(`figure-set`)
  figureSet.append(set.original);
  figureSet.append(set.compare);
  specificDiff.append(figureSet);
  section.append(specificDiff);
}

/**
 * ... docs go here...
 */
 function buildImage(browserWidth, diff) {
  const original = `./${referenceId}/${browserWidth}/${diff}/screenshot.png`;
  const diffBase = `./${compareId}/${browserWidth}/${diff}`;
  const compare = `${diffBase}/screenshot.png`;
  const originalMask = `${diffBase}/original_mask.png`;
  const diffMask = `${diffBase}/diff_mask.png`;

  return {
    diff,
    browserWidth,
    original: buildImageElement(original, originalMask, "reference"),
    compare: buildImageElement(compare, diffMask, "compare"),
  };
}

/**
 * ... docs go here...
 */
 function buildImageElement(screenshot, overlay, classes='') {
  const figure = create(`figure`);
  figure.setAttribute(`style`, `
    background-image: url("${screenshot}");
  `);

  let img = new Image();
  img.src = screenshot;
  img.style.width = `100%`;
  img.classList.add(`for-sizing-only`);
  figure.append(img);

  img = new Image();
  img.src = overlay;
  img.style.width = `100%`;
  img.classList.add(classes, `overlay`);
  figure.append(img);
  return figure;
}
