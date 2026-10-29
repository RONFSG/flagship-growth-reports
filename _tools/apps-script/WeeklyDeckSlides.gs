/**
 * Weekly deck -> editable Google Slides, for every brand that publishes a weekly deck.
 *
 * The weekly deck run publishes, next to each brand's PowerPoint, the Google Slides requests that rebuild the
 * same deck as real text boxes, tables and shapes (slides-requests.json.gz, written by
 * _tools/dormeo-us-deck/slides_requests.py). This script sends them into the brand's ONE Google Slides file, so
 * the design stays the PowerPoint's and nothing here needs changing when the slides change.
 *
 * Which brands: https://reports.flagshipgrowth.com/decks.json (written by `deck.py index` from
 * _tools/deck-schedule.json). A new brand is picked up on the next run, no edit here.
 * Which file: the brand's manifest "googleSlides" link (its googleSlidesId in deck-schedule.json; Insights opens
 * the same link). A brand without one gets a new file; the log prints its id to put in deck-schedule.json.
 *
 * Setup (once): _tools/apps-script/README.md. Needs the "Google Slides API" service (Services +). Run setup().
 */
const INDEX_URL = 'https://reports.flagshipgrowth.com/decks.json';
const FOLDER_NAME = 'Weekly decks';   // new files go here if a folder with this name exists in your Drive

function setup() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'updateDecks')
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('updateDecks').timeBased().everyMinutes(30).create();
  updateDecks();
}

const fresh_ = (url) => url + (url.indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now();

/** Every brand: rebuild its Slides file when a new deck (or the Tuesday inventory rebuild) has been published. */
function updateDecks() {
  const props = PropertiesService.getScriptProperties();
  const brands = JSON.parse(UrlFetchApp.fetch(fresh_(INDEX_URL)).getContentText()).brands || [];
  brands.forEach((b) => {
    try {
      const res = UrlFetchApp.fetch(fresh_(b.manifest), { muteHttpExceptions: true });
      if (res.getResponseCode() === 404) { console.log(b.name + ': no deck published yet'); return; }   // switched on, first run still to come
      const man = JSON.parse(res.getContentText());
      const cur = man.current || {};
      if (!cur.slidesRequests) { console.log(b.name + ': no Slides requests published yet'); return; }
      const base = b.manifest.replace(/manifest\.json$/, '');
      const blob = UrlFetchApp.fetch(fresh_(base + cur.slidesRequests)).getBlob().setContentType('application/x-gzip');
      const deck = JSON.parse(Utilities.ungzip(blob).getDataAsString());

      const linked = /\/presentation\/d\/([A-Za-z0-9_-]+)/.exec(man.googleSlides || '');
      const fileId = (linked && linked[1]) || props.getProperty('file:' + b.slug) || createFile_(b, props);
      const key = 'run:' + b.slug + ':' + fileId;
      if (props.getProperty(key) === deck.run) { console.log(b.name + ': up to date (week ' + cur.week + ')'); return; }

      rebuild_(fileId, deck);
      props.setProperty(key, deck.run);
      console.log(b.name + ': week ' + cur.week + ' loaded, ' + deck.slides + ' slides -> https://docs.google.com/presentation/d/' + fileId + '/edit');
    } catch (e) {
      console.error(b.name + ': ' + e);
    }
  });
}

/** Adds the new slides in front of the old ones, then deletes the old ones. If a batch fails, the new slides
 *  are removed again, so the file always shows one complete deck. */
function rebuild_(fileId, deck) {
  const ids = () => (Slides.Presentations.get(fileId, { fields: 'slides.objectId' }).slides || []).map((s) => s.objectId);
  const old = ids();
  try {
    deck.batches.forEach((reqs) => Slides.Presentations.batchUpdate({ requests: reqs }, fileId));
  } catch (e) {
    const added = ids().filter((id) => old.indexOf(id) < 0);
    if (added.length) Slides.Presentations.batchUpdate({ requests: added.map((id) => ({ deleteObject: { objectId: id } })) }, fileId);
    throw e;
  }
  if (old.length) Slides.Presentations.batchUpdate({ requests: old.map((id) => ({ deleteObject: { objectId: id } })) }, fileId);
}

function createFile_(b, props) {
  const id = Slides.Presentations.create({ title: b.name + ' - Weekly deck (editable)' }).presentationId;   // 16:9, like the deck
  const folders = DriveApp.getFoldersByName(FOLDER_NAME);
  if (folders.hasNext()) DriveApp.getFileById(id).moveTo(folders.next());
  props.setProperty('file:' + b.slug, id);
  console.log(b.name + ': created https://docs.google.com/presentation/d/' + id + '/edit  ->  set googleSlidesId "' + id + '" for ' + b.slug + ' in _tools/deck-schedule.json');
  return id;
}

/** Forget what was loaded, so the next run rebuilds every brand's file (e.g. after editing a slide by hand). */
function reloadAll() {
  const props = PropertiesService.getScriptProperties();
  props.getKeys().filter((k) => k.indexOf('run:') === 0).forEach((k) => props.deleteProperty(k));
  updateDecks();
}
