/**
 * Weekly deck -> editable Google Slides (trial, side by side with the picture copy).
 *
 * The weekly deck run publishes, next to each brand's PowerPoint, the Google Slides requests that rebuild the
 * same deck as real text boxes, tables and shapes (slides-requests.json.gz, written by
 * _tools/dormeo-us-deck/slides_requests.py). This script fetches them and sends them to ONE Google Slides file
 * per brand, so the design stays the PowerPoint's and nothing here needs changing when the slides change.
 *
 * Setup (once): see _tools/apps-script/README.md. In short: paste this file into a new project at
 * script.google.com, add the "Google Slides API" service (Services +), run setup() and allow access.
 * setup() runs it once now and then every 30 minutes on its own.
 *
 * While this is a trial, each brand gets its own NEW file ("<brand> - Weekly deck (editable)"); the
 * picture-copy file the deck run updates is never touched. To switch over later, put that file's id in
 * fileId below.
 */
const BRANDS = [
  { name: 'Dormeo US', manifest: 'https://reports.flagshipgrowth.com/dormeo-us/deck/manifest.json', fileId: '' },
  { name: 'Dormeo Canada', manifest: 'https://reports.flagshipgrowth.com/dormeo-canada/deck/manifest.json', fileId: '' },
];
const FOLDER_NAME = 'Weekly decks';   // new files go here if a folder with this name exists in your Drive

function setup() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'updateDecks')
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('updateDecks').timeBased().everyMinutes(30).create();
  updateDecks();
}

/** Every brand: rebuild its Slides file when a new deck (or the Tuesday inventory rebuild) has been published. */
function updateDecks() {
  const props = PropertiesService.getScriptProperties();
  BRANDS.forEach((b) => {
    try {
      const man = JSON.parse(UrlFetchApp.fetch(b.manifest + '?t=' + Date.now()).getContentText());
      const cur = man.current || {};
      if (!cur.slidesRequests) { console.log(b.name + ': no Slides requests published yet'); return; }
      const base = b.manifest.replace(/manifest\.json$/, '');
      const blob = UrlFetchApp.fetch(base + cur.slidesRequests + '?t=' + Date.now()).getBlob().setContentType('application/x-gzip');
      const deck = JSON.parse(Utilities.ungzip(blob).getDataAsString());
      const key = 'run:' + b.name;
      if (props.getProperty(key) === deck.run) { console.log(b.name + ': up to date (week ' + cur.week + ')'); return; }

      const fileId = b.fileId || props.getProperty('file:' + b.name) || createFile_(b.name, props);
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
  const old = (Slides.Presentations.get(fileId, { fields: 'slides.objectId' }).slides || []).map((s) => s.objectId);
  try {
    deck.batches.forEach((reqs) => Slides.Presentations.batchUpdate({ requests: reqs }, fileId));
  } catch (e) {
    const now = (Slides.Presentations.get(fileId, { fields: 'slides.objectId' }).slides || []).map((s) => s.objectId);
    const added = now.filter((id) => old.indexOf(id) < 0);
    if (added.length) Slides.Presentations.batchUpdate({ requests: added.map((id) => ({ deleteObject: { objectId: id } })) }, fileId);
    throw e;
  }
  if (old.length) Slides.Presentations.batchUpdate({ requests: old.map((id) => ({ deleteObject: { objectId: id } })) }, fileId);
}

function createFile_(name, props) {
  const id = Slides.Presentations.create({ title: name + ' - Weekly deck (editable)' }).presentationId;   // 16:9, like the deck
  const folders = DriveApp.getFoldersByName(FOLDER_NAME);
  if (folders.hasNext()) DriveApp.getFileById(id).moveTo(folders.next());
  props.setProperty('file:' + name, id);
  console.log(name + ': created https://docs.google.com/presentation/d/' + id + '/edit');
  return id;
}

/** Forget what was loaded, so the next run rebuilds every brand's file (e.g. after editing a slide by hand). */
function reloadAll() {
  const props = PropertiesService.getScriptProperties();
  BRANDS.forEach((b) => props.deleteProperty('run:' + b.name));
  updateDecks();
}
