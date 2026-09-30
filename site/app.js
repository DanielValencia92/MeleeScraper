const eventBody = document.querySelector('#events');
const count = document.querySelector('#count');
const format = document.querySelector('#format');
const search = document.querySelector('#search');

function text(value) { return value ?? '—'; }
function location(event) { return [event.city, event.region, event.country].filter(Boolean).join(', ') || '—'; }
function render(events) {
  eventBody.replaceChildren(...events.map(event => {
    const row = document.createElement('tr');
    const title = document.createElement('a'); title.href = event.url; title.textContent = text(event.name); title.target = '_blank'; title.rel = 'noreferrer';
    const cells = [[title], [text(event.format_norm)], [location(event)], [text(event.player_count)], [text(event.source)]];
    for (const contents of cells) { const cell = document.createElement('td'); contents.forEach(item => cell.append(item)); row.append(cell); }
    return row;
  }));
  count.textContent = `${events.length} observed event${events.length === 1 ? '' : 's'}`;
}

Promise.all([fetch('data/events.json').then(r => r.json()), fetch('data/summary.json').then(r => r.json())])
  .then(([events, summary]) => {
    const metrics = document.querySelector('#metrics');
    metrics.innerHTML = `<article><strong>${summary.discovered || 0}</strong><span>URLs discovered</span></article><article><strong>${summary.parsed_events || 0}</strong><span>events parsed</span></article><article><strong>${summary.succeeded || 0}</strong><span>successful fetches</span></article>`;
    [...new Set(events.map(event => event.format_norm))].sort().forEach(value => format.add(new Option(value, value)));
    function update() {
      const needle = search.value.trim().toLowerCase();
      render(events.filter(event => (!format.value || event.format_norm === format.value) && (!needle || [event.name, event.city, event.country].filter(Boolean).join(' ').toLowerCase().includes(needle))));
    }
    format.addEventListener('change', update); search.addEventListener('input', update); update();
  })
  .catch(() => { count.textContent = 'No published dataset yet. Run “swu-play build-site” after a collection.'; });

