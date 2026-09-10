"""Build the isolated UI preview from the existing Atlas calendar and mixed UI.

No private data is read. The original app sources are never modified.
Run from any directory with Python 3.10+; output is a standalone HTML file.
"""
from pathlib import Path
from datetime import date, timedelta
import json
import re
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'prototype/atlas-apercu-complet-2026-09-10.html'
BASE = ROOT / 'prototype/atlas-audit-mixte-2026-09-10.html'

def js(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')

def build_program():
    """A synthetic UI fixture, not a generated prescription or a user's plan."""
    weeks = []
    for n in range(10):
        start = date(2026, 8, 17) + timedelta(weeks=n)
        workouts = []
        for day, title, duration, kind, zone in [
            (1, '6 × 3 min VO₂max', 53, 'vma_long', 5),
            (3, '3 × 8 min sous SV2', 59, 'threshold_sv2', 4),
            (5, 'Endurance fondamentale · Z2', 50, 'endurance_z2', 2),
        ]:
            when = (start + timedelta(days=day)).isoformat()
            target = {'zone': zone, 'speed_min_kmh': {2: 9, 4: 11.8, 5: 13.4}[zone],
                      'speed_max_kmh': {2: 10, 4: 12.2, 5: 13.8}[zone]}
            easy = {'zone': 2, 'speed_min_kmh': 9, 'speed_max_kmh': 10}
            blocks = [{'block_type': 'warm_up', 'name': 'Échauffement', 'duration_minutes': 15, 'target': easy}]
            if day == 1:
                blocks += [{'block_type': 'work', 'name': '6 × 3 min', 'duration_minutes': 3,
                            'repetitions': 6, 'recovery_minutes': 2, 'target': target}]
            elif day == 3:
                blocks += [{'block_type': 'work', 'name': '3 × 8 min', 'duration_minutes': 8,
                            'repetitions': 3, 'recovery_minutes': 5, 'target': target}]
            else:
                blocks += [{'block_type': 'continuous', 'name': 'Endurance', 'duration_minutes': 25, 'target': target}]
            blocks += [{'block_type': 'cool_down', 'name': 'Retour au calme', 'duration_minutes': 10,
                        'target': {'zone': 1, 'speed_min_kmh': 8, 'speed_max_kmh': 9}}]
            workouts.append({'workout_id': when + '-demo-' + kind, 'workout_date': when,
                             'title': title, 'sport': 'running', 'workout_type': kind,
                             'planned_duration_minutes': duration, 'blocks': blocks,
                             'objective': 'Séance fictive pour parcourir la présentation du calendrier existant.',
                             'coach_notes': ['Exemple de présentation uniquement, sans prescription personnalisée.'],
                             'expected_response': {
                                 'physiological_load_0_100': {2: 28, 4: 60, 5: 76}[zone],
                                 'biomechanical_load_0_100': {2: 25, 4: 55, 5: 65}[zone]}})
        weeks.append({'week_number': n + 1, 'start_date': start.isoformat(),
                      'end_date': (start + timedelta(days=6)).isoformat(),
                      'phase': 'development', 'objective': 'Semaine de démonstration · données fictives',
                      'target_duration_minutes': sum(w['planned_duration_minutes'] for w in workouts),
                      'workouts': workouts})
    return {'start_date': weeks[0]['start_date'], 'end_date': weeks[-1]['end_date'],
            'duration_weeks': 10, 'total_running_workouts': 30, 'weeks': weeks,
            'goal': {'name': 'Semi-marathon · exemple', 'event_date': '2026-10-25',
                     'target_time_minutes': 110, 'distance_km': 21.1},
            'settings': {'optional_running_sessions_per_week': 1},
            'historical_completed_workouts': []}

FRAME_ADAPTER = r'''
const nativeWindow = window;
const nativeDate = Date;
const demoMemory = new Map();
const demoStore = {getItem: key => demoMemory.get(key) ?? null,
  setItem: (key, value) => demoMemory.set(key, String(value)),
  removeItem: key => demoMemory.delete(key)};
const demoHistory = {state: null, pushState(value) {this.state = value}, back() {this.state = null}};
const previewWindow = new Proxy(nativeWindow, {get(target, key) {
  if (key === 'history') return demoHistory;
  const value = Reflect.get(target, key, target);
  return typeof value === 'function' && ['addEventListener','removeEventListener','matchMedia',
    'requestAnimationFrame','setTimeout','clearTimeout','alert','confirm','prompt'].includes(key)
    ? value.bind(target) : value;
}});
class DemoDate extends nativeDate {
  constructor(...args) {super(...(args.length ? args : ['2026-09-10T12:00:00']))}
  static now() {return new nativeDate('2026-09-10T12:00:00').getTime()}
}
function demoNotice(message) {
  const notice = document.getElementById('legacyNotice');
  notice.textContent = message;
  notice.hidden = false;
  clearTimeout(demoNotice.timer);
  demoNotice.timer = setTimeout(() => {notice.hidden = true}, 6500);
}
async function demoFetch(input, options = {}) {
  const path = String(input).split('?')[0];
  const read = !options.method || options.method === 'GET';
  let payload = {ok: true};
  if (!read) {
    payload = {ok: false, error: 'Aperçu : cette action nécessite le moteur Atlas et ne modifie aucune donnée.'};
    demoNotice(payload.error);
  } else if (path === '/api/atlas-coach/program') payload = demoProgram;
  else if (path === '/api/atlas-coach/executions') payload.executions = [];
  else if (path === '/api/atlas-coach/workout-decisions') payload.decisions = {};
  else if (path === '/api/atlas-coach/historical-workouts' || path === '/api/atlas-coach/optional-workouts') payload.workouts = [];
  else if (path === '/api/atlas-coach/workout-context') payload.context = null;
  else if (path === '/api/atlas-coach/daily-preparation') {payload.preparation = null; payload.selection = null;}
  else payload = {ok: false, error: 'Cette source n’est pas chargée dans l’aperçu fictif.'};
  return {ok: payload.ok !== false, status: payload.ok === false ? 400 : 200, json: async () => payload};
}
document.addEventListener('click', event => {
  if (event.target.closest('[data-workout-action], [data-recalculate-execution], [data-reschedule], [data-reschedule-workout]')) {
    event.preventDefault(); event.stopImmediatePropagation();
    demoNotice('Aperçu : consultation du plan uniquement. Ton programme réel reste inchangé.');
  }
}, true);
document.getElementById('printButton').onclick = () => nativeWindow.print();
'''

SHELL_CSS = r'''
/* Navigation explicite : aucun libellé masqué sur tablette ou smartphone. */
.shell{grid-template-columns:225px minmax(0,1fr)}
.rail button{white-space:normal;min-width:0;line-height:1.35}.rail button span{display:block;font-size:14px}
.rail-note{display:none}.rail nav{gap:8px}.rail button i{flex:0 0 24px}
.legacy-host{min-width:0}.legacy-frame{display:block;width:100%;height:850px;border:1px solid var(--edge);border-radius:16px;background:#020713}
.legacy-intro .topline{margin-bottom:16px}.legacy-intro p{max-width:70ch}
.connect-hero{padding:24px;background:linear-gradient(130deg,#0a2c3d,#0b1b30);border:1px solid #2e6677;border-radius:17px;margin-bottom:22px}
.connect-hero h2{margin:8px 0}.connect-hero p{color:var(--muted)}.connect-heading{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.connect-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.connect-actions button{flex:1;min-width:180px}
.connect-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:18px}
.connect-source{border:1px solid var(--edge);border-radius:14px;padding:20px;min-width:0}.connect-source p{margin:8px 0 16px;color:var(--muted);font-size:15px}.connect-source .source-pill{margin-bottom:12px}
.inventory{display:grid;gap:0}.inventory .row{gap:15px}.inventory .row>span{text-align:right;color:var(--muted);font-size:14px}.inventory .row strong{font-size:15px}
.connection-status{font-size:14px;padding:6px 10px;border-radius:8px;border:1px solid #3e6d72;align-self:start;color:#98e2d1;white-space:normal}
.connect-dialog-copy{color:var(--muted);margin-top:14px}.connection-check{display:flex;gap:12px;align-items:center;margin:18px 0}.connection-check input{width:20px;height:20px}.connect-details-list{padding-left:22px;color:var(--muted);line-height:1.8}
@container(max-width:1100px){.shell{grid-template-columns:195px minmax(0,1fr)}.rail{padding:22px 12px}.rail button{justify-content:flex-start;padding:11px 10px}.rail button span{display:block}.brand{margin-bottom:25px}.content{padding:22px 18px}}
@container(max-width:850px){.shell{display:block}.rail{position:static;height:auto;padding:13px 16px;border-right:0;border-bottom:1px solid var(--edge)}.brand{margin:0 0 10px}.rail nav{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}.rail button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:9px 5px;text-align:center}.rail button i{flex:auto}.connect-grid{grid-template-columns:1fr 1fr}}
@container(max-width:600px){.rail{padding:10px 12px}.rail nav{grid-template-columns:repeat(4,minmax(0,1fr));gap:5px}.rail button{min-height:69px;padding:7px 2px}.rail button span{font-size:14px;line-height:1.3;hyphens:auto;overflow-wrap:anywhere}.rail button[data-view="connections"]{grid-column:1/-1;flex-direction:row;min-height:44px;gap:10px;border:1px solid var(--edge)}.rail button[data-view="connections"] span{font-size:14px}.rail button[data-view="connections"] i{flex:0 0 22px}.content{padding:17px 12px 24px}.connect-grid{grid-template-columns:1fr}.connect-hero{padding:19px 16px}.connect-actions{flex-direction:column}.connect-actions button{width:100%;min-width:0}.legacy-frame{height:800px;border-radius:12px}.legacy-intro h1{font-size:27px}.inventory .row{align-items:flex-start}}
'''

CONNECTIONS_JS = r'''
const connectionDemo = {syncing:false, synced:false, auto:true};
function connections(){return title('CONNEXIONS & DONNÉES','Vos données dans Atlas','Les sources, la synchronisation et les données disponibles, réunies au même endroit.')+`
  <section class="connect-hero"><div class="connect-heading"><div><p class="eyebrow">ATLAS CONNECT</p><h2>Santé Connect</h2><p>Activités et données de santé partagées depuis Android.</p></div><span class="connection-status">Exemple : source reliée</span></div>
  <div class="connect-actions"><button class="primary" data-connection="sync" ${connectionDemo.syncing?'disabled':''}>${connectionDemo.syncing?'Simulation en cours…':'Simuler une synchronisation'}</button><button data-connection="permissions">Autorisations</button><button data-connection="settings">Paramètres</button></div>
  <p id="syncDemoStatus" class="source-line" role="status">${connectionDemo.synced?'Simulation terminée : aucune nouvelle donnée dans cet exemple.':'Dernière synchronisation fictive : 10 septembre, 09 h 05.'}</p></section>
  <section><div class="section-head"><h2>Ajouter ou gérer une source</h2></div><div class="connect-grid">
  <article class="connect-source"><span class="source-pill">Fichiers Garmin</span><h3>Activités & Wellness</h3><p>Les activités FIT et les archives de récupération restent deux sources distinctes.</p><button data-connection="garmin">Voir le parcours d’import</button></article>
  <article class="connect-source"><span class="source-pill">Profil manuel</span><h3>Continuer sans montre</h3><p>Retrouver les repères et les informations de votre profil.</p><button data-action="profile">Ouvrir le profil →</button></article></div>
  <details><summary>Autres montres et services</summary><p>Polar, Suunto et COROS : disponibilité à vérifier dans les connexions réelles d’Atlas. Aucun compte n’est relié dans cet aperçu.</p></details></section>
  <section class="panel" style="margin-top:24px"><h2>Ce qu’Atlas reçoit</h2><p class="source-line">Inventaire fictif, indépendant des autorisations.</p><div class="inventory">
  <div class="row"><div><strong>Activités</strong><p>Fichiers FIT Garmin</p></div><span>Disponibles dans l’exemple</span></div>
  <div class="row"><div><strong>Sommeil & récupération</strong><p>Archive Garmin Wellness</p></div><span>Disponibles dans l’exemple</span></div>
  <div class="row"><div><strong>VFC</strong><p>Archive Garmin Wellness</p></div><span>Aucune valeur issue de Santé Connect dans cet exemple</span></div>
  <div class="row"><div><strong>Données mécaniques</strong><p>Selon la montre et l’activité</p></div><span>Couverture incomplète</span></div></div>
  <p class="source-line">Une autorisation ne garantit pas qu’une donnée a été reçue. Les valeurs absentes restent signalées comme telles.</p></section>`}
function connectionDialog(kind){
  const texts={
    permissions:['Autorisations Santé Connect',`<p>Dans Atlas sur Android, ce bouton ouvre les autorisations du téléphone.</p><ul class="connect-details-list"><li>Activités sportives</li><li>Fréquence cardiaque</li><li>Sommeil et autres données autorisées</li></ul><p>Les autorisations réelles et leur couverture seront lues sur ton téléphone.</p>`],
    settings:['Paramètres de connexion',`<label class="connection-check"><input id="autoDemo" type="checkbox" ${connectionDemo.auto?'checked':''}> Synchronisation automatique dans l’exemple</label><p>Ce réglage illustre le parcours. Il reste en mémoire uniquement pendant l’ouverture de l’aperçu.</p>`],
    garmin:['Importer Garmin',`<div class="connect-grid"><article class="connect-source"><h3>Activités FIT</h3><p>Les séances, les tours et les flux enregistrés par la montre.</p></article><article class="connect-source"><h3>Archive Wellness</h3><p>Le sommeil, la VFC et les autres repères présents dans l’archive.</p></article></div><p>Le choix des fichiers et l’import réel restent dans l’application Atlas. Cet aperçu ne lit aucun fichier personnel.</p>`]
  };
  const [heading,body]=texts[kind];$('#connectionTitle').textContent=heading;$('#connectionBody').innerHTML=body;
  $('#connectionDialog').showModal();$('#autoDemo')?.addEventListener('change',e=>{connectionDemo.auto=e.target.checked});
}
function bindConnections(){
  $$('[data-connection]').forEach(button=>button.onclick=()=>{
    const action=button.dataset.connection;
    if(action!=='sync'){connectionDialog(action);return}
    connectionDemo.syncing=true;render();
    setTimeout(()=>{connectionDemo.syncing=false;connectionDemo.synced=true;if(state.view==='connections')render()},900);
  });
}
let legacyFrame = null;
function mountLegacyPlan(){
  const host=$('#legacyHost');host.hidden=state.view!=='plan';
  if(state.view==='plan'&&!legacyFrame){
    legacyFrame=document.createElement('iframe');legacyFrame.className='legacy-frame';
    legacyFrame.title='Plan d’entraînement Atlas : calendrier et fiches de séance d’origine';
    legacyFrame.setAttribute('sandbox','allow-scripts allow-modals');legacyFrame.srcdoc=legacyDocument;
    host.appendChild(legacyFrame);
  }
}
'''

def main():
    base = BASE.read_text()
    avatar = re.search(r"const avatar=('.*?');", base).group(1)
    original_calendar = (ROOT / 'app/js/atlas-training-calendar.js').read_text()
    calendar = original_calendar
    for name in ['homme','femme']:
        calendar = calendar.replace('"./assets/atlas-avatar-' + name + '-clean-final.png?v=2"', 'ATLAS_DEMO_AVATAR')
    css_files = ['app/css/performance-running.css', 'app/css/atlas-responsive.css']
    css = '\n'.join((ROOT / f).read_text() for f in css_files)
    original_html = (ROOT / 'app/performance-running.html').read_text()
    css += '\n' + re.search(r'<style[^>]*>(.*?)</style>', original_html, re.S).group(1)
    # Only the surrounding page chrome is adjusted; the calendar styles and
    # their original PC/tablet/mobile media queries remain intact.
    css += '''\n.performance-header{display:none!important}.performance-app{width:100%;padding:0!important;margin:0}
    #planPanel{margin:0!important;border-radius:14px} .coach-workspace{display:block!important}
    #legacyNotice{position:fixed;bottom:14px;left:12px;right:12px;z-index:99999;background:#153a50;border:1px solid #60ccef;color:white;padding:15px;border-radius:12px;font:14px/1.5 system-ui}
    .plan-title p{font-size:12px!important}.plan-title h2{font-size:22px!important}
    @media print{#legacyNotice,#printButton{display:none!important}.premium-week{break-inside:avoid}.premium-week:not([open])>*{display:block}.calendar-day{display:block!important}.performance-app{padding:0}}
    '''
    panel = original_html[original_html.index('  <section class="panel plan-panel'):]
    panel = panel[:panel.index('</section>') + len('</section>')]
    panel = panel.replace(' hidden>', '>').replace('ÉTAPE 3','EXEMPLE FICTIF · CALENDRIER D’ORIGINE')
    panel = panel.replace('coach-section-panel"', 'coach-section-panel is-coach-active"')
    program = build_program()
    frame = '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    frame += '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; connect-src \'none\'; form-action \'none\'; base-uri \'none\'">'
    frame += '<title>Plan d’entraînement Atlas · aperçu fictif</title><style>' + css + '</style></head><body>'
    frame += '<header class="performance-header"></header><main class="performance-app"><div class="coach-workspace">' + panel + '</div></main><div id="legacyNotice" role="status" hidden></div>'
    frame += '<script>\nconst ATLAS_DEMO_AVATAR=' + avatar + ';\nconst demoProgram=' + js(program) + ';\n' + FRAME_ADAPTER
    frame += '\n(function(window,localStorage,fetch,Date){\n' + calendar + '\n})(previewWindow,demoStore,demoFetch,DemoDate);\n</script></body></html>'
    base = re.sub(r'<title>.*?</title>', '<title>Atlas · Santé, navigation et plan d’origine</title>', base, count=1)
    base = base.replace("connect-src 'none';", "connect-src 'none'; frame-src 'self' about:;", 1)
    base = base.replace('</style></head>', SHELL_CSS + '\n</style></head>', 1)
    base = re.sub(r'<header class="workbench"><div>.*?</div>', '<header class="workbench"><div><strong>Atlas · Nouvel aperçu complet</strong><p>Santé, navigation et calendrier d’origine · données fictives.</p></div>', base, count=1)
    base = base.replace('<span>Plan</span>', '<span>Plan d’entraînement</span>')
    base = base.replace('<span>Santé</span></button></nav>', '<span>Santé</span></button><button data-view="connections"><i aria-hidden="true">⇄</i><span>Connexions &amp; données</span></button></nav>', 1)
    base = base.replace('<main class="content" id="main" tabindex="-1"></main>', '<main class="content" id="main" tabindex="-1"><div id="viewContent"></div><section id="legacyHost" class="legacy-host" hidden aria-label="Calendrier d’origine"></section></main>')
    base = base.replace("view:'today'", "view:'health'", 1)
    base = re.sub(r'const meta=.*?;\n', 'const meta=\'<div class="demo-note">APERÇU FICTIF · Aucune connexion à tes données réelles.</div>\';\n', base, count=1)
    start, end = base.index('function plan(){'), base.index('function blocks(')
    # Preserve all other pages, including the validated Health module.
    base = base[:start] + '''function plan(){return `<section class="legacy-intro">`+title('PLAN D’ENTRAÎNEMENT','Votre calendrier Atlas','Semaines, journées et fiches de séance : la présentation d’origine.')+`<p class="meta">Programme fictif sur 10 semaines. Ouvre une semaine, puis une séance pour retrouver son déroulé et ses étapes. Aucun compte rendu réel n’est chargé.</p></section>`}\n''' + base[end:]
    base = base.replace("?'au plan':", "?'au plan d’entraînement':")
    base = base.replace('Consulter le plan</button>', 'Consulter le plan d’entraînement</button>')
    base = base.replace('Voir le plan →', 'Voir le plan d’entraînement →')
    base = base.replace('const pages={today,profile,plan,report,health};', 'const pages={today,profile,plan,report,health,connections};')
    base = base.replace("$('#main').innerHTML=", "$('#viewContent').innerHTML=")
    base = re.sub(r'\+`<footer>Atlas,.*?</footer>`;', '+(state.view===\'plan\'?\'\':`<footer>Atlas · Aperçu fictif du 10 septembre 2026.</footer>`);mountLegacyPlan();bindConnections();', base, count=1)
    base = base.replace("$('#closeMetric').onclick", "$('#closeConnection').onclick=()=>$('#connectionDialog').close();$('#closeMetric').onclick")
    extra_dialog = '<dialog id="connectionDialog" aria-labelledby="connectionTitle"><div class="section-head"><h2 id="connectionTitle">Connexion</h2><button id="closeConnection">Fermer</button></div><div id="connectionBody" class="connect-dialog-copy"></div></dialog>'
    base = base.replace('<script>\n', extra_dialog + '\n<script>\nconst legacyDocument=' + js(frame) + ';\n' + CONNECTIONS_JS, 1)
    digest = hashlib.sha256(original_calendar.encode()).hexdigest()
    base = base.replace('<!doctype html>', '<!doctype html>\n<!-- Calendar source: app/js/atlas-training-calendar.js; SHA256 ' + digest + '. Generated by scripts/build_atlas_complete_preview.py. -->', 1)
    OUTPUT.write_text(base)
    print(f'Created {OUTPUT.name}: {OUTPUT.stat().st_size} bytes; calendar SHA256 {digest}')

if __name__ == '__main__':
    main()
