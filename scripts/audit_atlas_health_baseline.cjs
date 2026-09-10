// Execute les fonctions exactes du fichier Sante dans un contexte Node factice.
// Aucun navigateur, aucun fichier de donnees privees et aucune requete reseau.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../app/js/atlas-hub.js'), 'utf8');
const values = new Map();
const ctx = {
  REPORTS_KEY: 'atlas.health.pain_reports.v2',
  LEGACY_REPORT_KEYS: ['atlasHealthPainReports', 'atlas.running_pain_reports.v2', 'atlas.running_pain_reports.v1'],
  regionLabels: { knee: 'Genou' }, sideLabels: { right: 'Droite' },
  read: key => JSON.parse(values.get(key) || '[]'),
  write: (key, value) => values.set(key, JSON.stringify(value)),
};
vm.createContext(ctx);
const normalization = source.slice(source.indexOf('  function normalizeReport('), source.indexOf('  function activate('));
if (!normalization.includes('function migrateReports')) throw new Error('Source changed; audit needs review');
vm.runInContext(normalization, ctx);
const report = { id: 'synthetic-knee', date: '2026-09-10', region: 'knee', side: 'right',
  zone: 'Region', intensity: 3, resolved: false };
ctx.write('atlas.running_pain_reports.v1', [report]);
const imported = ctx.allReports();
imported[0].resolved = true;
ctx.saveReports(imported);
const canonicalBeforeRead = ctx.read(ctx.REPORTS_KEY)[0].resolved;
const resolvedAfterRead = ctx.allReports()[0].resolved;
const dateFunction = source.slice(source.indexOf('  function executionDate('), source.indexOf('  function activityOf('));
vm.runInContext(dateFunction, ctx);
const apiDateRead = ctx.executionDate({ start_time: '2026-09-09T18:00:00Z', activity: { sport: 'running', distance_km: 10 } });
console.log(JSON.stringify({ synthetic_only: true,
  legacy_resolution: { canonicalBeforeRead, resolvedAfterRead },
  api_top_level_start_time: { expectedDatePresent: true, result: apiDateRead }
}, null, 2));
