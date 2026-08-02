import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_BASE = '../assets/models/anatomy/lower-limb/';
const LAYERS = {
  squelette: { file: 'atlas_membre_inferieur_squelette.glb', label: 'Squelette', count: 66, visible: true },
  articulations: { file: 'atlas_membre_inferieur_articulations.glb', label: 'Articulations', count: 176, visible: true },
  muscles_tendons: { file: 'atlas_membre_inferieur_muscles_tendons.glb', label: 'Muscles & tendons', count: 229, visible: true },
  insertions: { file: 'atlas_membre_inferieur_insertions.glb', label: 'Insertions', count: 201, visible: false }
};

const canvas = document.querySelector('#anatomyCanvas');
const viewport = document.querySelector('#viewport');
const loadingPanel = document.querySelector('#loadingPanel');
const loadingBar = document.querySelector('#loadingBar');
const loadingLabel = document.querySelector('#loadingLabel');
const objectCount = document.querySelector('#objectCount');
const engineState = document.querySelector('#engineState');
const renderStats = document.querySelector('#renderStats');
const selectionTag = document.querySelector('#selectionTag');
const interactionHelp = document.querySelector('#interactionHelp');
const twinStorage = window.AtlasTwinStorage ? new window.AtlasTwinStorage() : null;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = .92;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x05090c, .045);

const camera = new THREE.PerspectiveCamera(32, 1, .01, 250);
camera.position.set(4.7, 2.5, 7.2);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = .055;
controls.enablePan = true;
controls.screenSpacePanning = true;
controls.minDistance = .5;
controls.maxDistance = 25;
controls.target.set(0, 0, 0);

scene.add(new THREE.HemisphereLight(0xe8f2f4, 0x17191c, 1.55));
const keyLight = new THREE.DirectionalLight(0xfff4e7, 3.35); keyLight.position.set(4, 7, 6); scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x65dce6, 1.45); rimLight.position.set(-5, 3, -4); scene.add(rimLight);
const fillLight = new THREE.DirectionalLight(0xffbdad, 1.05); fillLight.position.set(4, 0, -3); scene.add(fillLight);
const frontLight = new THREE.DirectionalLight(0xffffff, 1.25); frontLight.position.set(0, 2, 8); scene.add(frontLight);

const floorGrid = new THREE.GridHelper(20, 28, 0x1c5660, 0x13242a);
floorGrid.material.transparent = true; floorGrid.material.opacity = .18; scene.add(floorGrid);

const anatomyRoot = new THREE.Group();
scene.add(anatomyRoot);

const loader = new GLTFLoader();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const loadedLayers = new Map();
const pickable = [];
let selected = null;
let hovered = null;
let isolated = false;
let fullBounds = null;
let pointerDown = null;

function resize() {
  const width = viewport.clientWidth;
  const height = viewport.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(height, 1);
  camera.updateProjectionMatrix();
}

function nameVariation(name, amount = .08) {
  let value = 0;
  for (let index = 0; index < name.length; index += 1) value = (value * 31 + name.charCodeAt(index)) >>> 0;
  return ((value % 1000) / 999 - .5) * amount;
}

function materialSpecification(name, layer) {
  const label = name.toLowerCase();

  if (layer === 'squelette') {
    return { color: 0xe7d9bd, roughness: .72, metalness: .02, opacity: 1 };
  }

  if (layer === 'insertions') {
    const origin = /\.o\d*/i.test(name);
    return { color: origin ? 0xd99642 : 0xf0bd69, roughness: .5, metalness: .03, opacity: .94 };
  }

  if (/meniscus/.test(label)) {
    return { color: 0x789a9c, roughness: .38, metalness: 0, opacity: .94, transmission: .05 };
  }
  if (/cartilage|articular surface/.test(label)) {
    return { color: 0xc9e7e5, roughness: .24, metalness: 0, opacity: .9, transmission: .08 };
  }
  if (/bursa|bursae|synovial/.test(label)) {
    return { color: 0x71c7d5, roughness: .2, metalness: 0, opacity: .42, transmission: .18 };
  }
  if (/ligament/.test(label)) {
    return { color: 0xd8c8a9, roughness: .62, metalness: 0, opacity: .98 };
  }
  if (/tendon|aponeurosis|fascia|tract|retinaculum|septum|sheath|arch/.test(label)) {
    return { color: 0xe9e2d3, roughness: .48, metalness: .015, opacity: .97 };
  }

  if (layer === 'muscles_tendons') {
    const color = new THREE.Color(0xa9363f);
    color.offsetHSL(nameVariation(name, .025), nameVariation(`${name}s`, .1), nameVariation(`${name}l`, .13));
    return { color, roughness: .64, metalness: 0, opacity: .96 };
  }

  return { color: 0xadd8dd, roughness: .34, metalness: 0, opacity: .86, transmission: .04 };
}

function anatomicalMaterial(name, layer) {
  const spec = materialSpecification(name, layer);
  const material = new THREE.MeshPhysicalMaterial({
    color: spec.color,
    roughness: spec.roughness,
    metalness: spec.metalness,
    transparent: spec.opacity < 1,
    opacity: spec.opacity,
    transmission: spec.transmission || 0,
    thickness: spec.transmission ? .08 : 0,
    clearcoat: layer === 'articulations' ? .18 : .04,
    clearcoatRoughness: .46,
    side: THREE.DoubleSide,
    depthWrite: spec.opacity >= .82
  });
  material.userData.originalColor = material.color.clone();
  material.userData.originalEmissive = material.emissive.clone();
  material.userData.originalEmissiveIntensity = material.emissiveIntensity;
  material.userData.originalOpacity = material.opacity;
  return material;
}

function anatomicalKey(name) {
  return String(name ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

function isSuperficialFascialEnvelope(name, layer) {
  if (layer !== 'muscles_tendons') return false;

  const key = anatomicalKey(name);

  return /^(fascialata|fascialatar|fascialatal|cruralfascia[lr]?|piriformisfascia[lr]?|poplitealfascia[lr]?)\d*$/.test(key);
}

function prepareModel(root, layer) {
  root.name = `ATLAS_${layer}`;
  root.userData.layer = layer;
  root.visible = LAYERS[layer].visible;
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.userData.layer = layer;
    object.userData.anatomicalName = object.name || 'Structure sans nom';
    if (isSuperficialFascialEnvelope(object.userData.anatomicalName, layer)) {
      object.visible = false;
      object.userData.hiddenByAtlas = 'superficial_fascial_envelope';
      return;
    }
    object.material = anatomicalMaterial(object.userData.anatomicalName, layer);
    object.castShadow = false;
    object.receiveShadow = false;
    pickable.push(object);
  });
}

function loadLayer(key, index) {
  const data = LAYERS[key];
  loadingLabel.textContent = `Chargement : ${data.label}`;
  return new Promise((resolve, reject) => {
    loader.load(MODEL_BASE + data.file, (gltf) => {
      prepareModel(gltf.scene, key);
      anatomyRoot.add(gltf.scene);
      loadedLayers.set(key, gltf.scene);
      loadingBar.style.width = `${((index + 1) / Object.keys(LAYERS).length) * 100}%`;
      resolve(gltf.scene);
    }, undefined, reject);
  });
}

async function loadAnatomy() {
  try {
    let index = 0;
    for (const key of Object.keys(LAYERS)) {
      await loadLayer(key, index++);
      objectCount.textContent = String([...loadedLayers.keys()].reduce((sum, k) => sum + LAYERS[k].count, 0));
    }
    fitWholeModel();
    engineState.textContent = 'Opérationnel';
    renderStats.textContent = `WEBGL · ${pickable.length} OBJETS`;
    setTimeout(() => loadingPanel.classList.add('done'), 350);
  } catch (error) {
    console.error(error);
    engineState.textContent = 'Erreur de chargement';
    loadingPanel.classList.add('done');
    showError('Impossible de charger les modèles 3D. Ouvrez cette page avec un serveur local (par exemple Live Server), et non directement comme un fichier Windows.');
  }
}

function fitBox(box, padding = 1.35) {
  if (!box || box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxSize = Math.max(size.x, size.y, size.z);
  const distance = (maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)))) * padding;
  const direction = new THREE.Vector3(.7, .28, 1).normalize();
  controls.target.copy(center);
  camera.position.copy(center).add(direction.multiplyScalar(distance));
  camera.near = Math.max(distance / 1000, .01);
  camera.far = distance * 50;
  camera.updateProjectionMatrix();
  controls.update();
  floorGrid.position.y = box.min.y - size.y * .035;
}

function fitWholeModel() {
  fullBounds = new THREE.Box3().setFromObject(anatomyRoot);
  fitBox(fullBounds, 1.25);
}

function restoreMaterial(object) {
  if (!object?.isMesh) return;
  const mats = Array.isArray(object.material) ? object.material : [object.material];
  mats.forEach((m) => {
    if (m.userData.originalColor && m.color) m.color.copy(m.userData.originalColor);
    if (m.userData.originalEmissive && m.emissive) m.emissive.copy(m.userData.originalEmissive);
    m.emissiveIntensity = m.userData.originalEmissiveIntensity ?? 1;
    m.opacity = m.userData.originalOpacity ?? 1;
  });
}

function accentMaterial(object, color, strength = .35) {
  const mats = Array.isArray(object.material) ? object.material : [object.material];
  mats.forEach((m) => {
    if (m.emissive) m.emissive.setHex(color);
    m.emissiveIntensity = strength;
    if (m.color) m.color.lerp(new THREE.Color(color), .1);
    m.opacity = Math.max(m.opacity, .95);
  });
}

function setPointer(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
}

function firstVisibleIntersection() {
  raycaster.setFromCamera(pointer, camera);
  return raycaster.intersectObjects(pickable.filter((o) => o.visible && o.parent?.visible), false)[0]?.object || null;
}

function onPointerMove(event) {
  if (pointerDown && Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y) > 4) return;
  setPointer(event);
  const hit = firstVisibleIntersection();
  if (hovered === hit || hit === selected) return;
  if (hovered && hovered !== selected) restoreMaterial(hovered);
  hovered = hit;
  if (hovered && hovered !== selected) accentMaterial(hovered, 0x37d8e8, .12);
  canvas.style.cursor = hovered ? 'pointer' : 'grab';
}

function onPointerDown(event) { pointerDown = { x: event.clientX, y: event.clientY }; }
function onPointerUp(event) {
  if (!pointerDown) return;
  const moved = Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y);
  pointerDown = null;
  if (moved > 5) return;
  setPointer(event);
  selectObject(firstVisibleIntersection());
}

function cleanAnatomicalName(name) {
  return name.replace(/\.(l|r)$/i, '').replace(/\.(o|e)\d*(l|r)$/i, '').trim();
}

function sideFromName(name) {
  if (/r$/i.test(name)) return 'DROIT';
  if (/l$/i.test(name)) return 'GAUCHE';
  return 'CENTRAL';
}

function typeFromName(name, layer) {
  if (/bursa|bursae/i.test(name)) return 'Bourse séreuse';
  if (/tendon/i.test(name)) return 'Tendon';
  if (/ligament/i.test(name)) return 'Ligament';
  if (/meniscus/i.test(name)) return 'Ménisque';
  if (/fascia|aponeurosis|tract|septum/i.test(name)) return 'Fascia / tissu conjonctif';
  if (/sheath/i.test(name)) return 'Gaine tendineuse';
  if (layer === 'insertions') return /\.o/i.test(name) ? 'Origine anatomique' : 'Terminaison anatomique';
  if (layer === 'muscles_tendons') return 'Muscle';
  if (layer === 'articulations') return 'Structure articulaire';
  return 'Structure osseuse';
}
function readPatientContext() {
  if (!twinStorage) return null;

  const twin = twinStorage.load();

  return {
    identity: twin.identity,
    pain: twin.function?.pain || [],
    professionalLoad: twin.profession?.physicalLoad ?? null,
    currentLoad: twin.performance?.running?.currentLoad || {},
    readiness: twin.performance?.running?.readiness || {},
    weeklyVolumeKm: twin.performance?.running?.weeklyVolumeKm ?? null
  };
}
function updateLoadUI(context) {
  const acuteLoad = Number(context?.currentLoad?.acute_load_7d);
  const chronicLoad = Number(context?.currentLoad?.chronic_load_28d);
  const readinessScore = Number(context?.readiness?.readiness_score);

  const hasAcuteLoad = Number.isFinite(acuteLoad);
  const hasChronicLoad = Number.isFinite(chronicLoad) && chronicLoad > 0;
  const hasReadiness = Number.isFinite(readinessScore);
  const hasProfessionalLoad = context?.professionalLoad !== null;

  if (hasAcuteLoad && hasChronicLoad) {
    const ratio = acuteLoad / chronicLoad;
    document.querySelector('#loadScore').textContent = `RATIO ${ratio.toFixed(2)}`;
    document.querySelector('#loadBar').style.width = `${Math.min(100, ratio * 50)}%`;
    document.querySelector('#loadExplanation').textContent =
      `Charge aiguë 7 j : ${acuteLoad}. Charge chronique 28 j : ${chronicLoad}. Analyse contextuelle disponible pour Atlas Brain.`;
    document.querySelector('#selectedLoad').textContent = `${acuteLoad} / ${chronicLoad}`;
    return;
  }

  if (hasReadiness) {
    document.querySelector('#loadScore').textContent = `${Math.round(readinessScore)}/100`;
    document.querySelector('#loadBar').style.width = `${Math.max(0, Math.min(100, readinessScore))}%`;
    document.querySelector('#loadExplanation').textContent =
      'Disponibilité physiologique disponible. Les charges aiguë et chronique restent à compléter.';
    document.querySelector('#selectedLoad').textContent = 'Disponibilité détectée';
    return;
  }

  if (hasProfessionalLoad) {
    document.querySelector('#loadScore').textContent = 'CHARGE PRO';
    document.querySelector('#loadBar').style.width = '35%';
    document.querySelector('#loadExplanation').textContent =
      'Charge professionnelle disponible. Les données sportives restent à compléter.';
    document.querySelector('#selectedLoad').textContent = 'Charge professionnelle';
    return;
  }

  document.querySelector('#loadScore').textContent = 'EN ATTENTE';
  document.querySelector('#loadBar').style.width = '18%';
  document.querySelector('#loadExplanation').textContent =
    'La structure est identifiée. ATLAS attend les données du patient et la charge récente pour calculer un indicateur personnalisé.';
  document.querySelector('#selectedLoad').textContent = 'Connexion requise';
}
function contextualAdvice(name, layer) {
  if (/calcaneal tendon|achilles/i.test(name)) return 'Corréler la sensibilité locale avec la charge de course récente, la raideur matinale et la tolérance aux contraintes élastiques.';
  if (/meniscus/i.test(name)) return 'Explorer les contraintes en flexion, rotation et appui, puis confronter la zone aux symptômes déclarés et à la charge récente.';
  if (/gluteus medius/i.test(name)) return 'Évaluer le contrôle frontal du bassin, la tolérance en appui unipodal et l’évolution de la charge des abducteurs.';
  if (/patellar/i.test(name)) return 'Analyser la charge du mécanisme extenseur, les volumes de flexion de genou et la réponse aux séances intensives.';
  if (layer === 'insertions') return 'Cette insertion peut être reliée au muscle ou au ligament parent pour analyser la chaîne de contrainte complète.';
  return 'Relier cette structure à la douleur déclarée, à la mobilité, aux activités récentes et aux indicateurs de récupération.';
}

function selectObject(object) {
  if (selected) restoreMaterial(selected);
  selected = object;
  if (!selected) { clearSelectionUI(); return; }
  accentMaterial(selected, 0x37d8e8, .65);
  const rawName = selected.userData.anatomicalName || selected.name;
  const layer = selected.userData.layer;
  const cleanName = cleanAnatomicalName(rawName);
  const side = sideFromName(rawName);
  const type = typeFromName(rawName, layer);
  const anatomicalSelection = {
    id: rawName,
    name: cleanName,
    side,
    type,
    layer,
    source: 'anatomy-3d',
    selectedAt: new Date().toISOString()
  };

    const patientContext = readPatientContext();
  const hasProfessionalLoad = patientContext?.professionalLoad !== null;
  const hasCurrentLoad = Object.keys(patientContext?.currentLoad || {}).length > 0;
  const hasReadiness = Object.keys(patientContext?.readiness || {}).length > 0;

  if (twinStorage) {
    twinStorage.update({
      anatomy: {
        currentSelection: anatomicalSelection
      },
      atlasBrain: {
        activeContext: {
          anatomy: anatomicalSelection,
          patient: patientContext,
          dataStatus: {
            professionalLoad: hasProfessionalLoad ? 'available' : 'missing',
            currentLoad: hasCurrentLoad ? 'available' : 'missing',
            readiness: hasReadiness ? 'available' : 'missing'
          },
          createdAt: new Date().toISOString()
        }
      }
    });
  }
  document.querySelector('#emptySelection').hidden = true;
  document.querySelector('#selectedContent').hidden = false;
  document.querySelector('#selectedName').textContent = cleanName;
  document.querySelector('#selectedSide').textContent = side;
  document.querySelector('#selectedType').textContent = type;
  document.querySelector('#selectedLayer').textContent = LAYERS[layer].label;
  document.querySelector('#selectedLoad').textContent = 'Connexion requise';
  document.querySelector('#selectionLayer').textContent = `${LAYERS[layer].label.toUpperCase()} · ${side}`;
  document.querySelector('#selectionName').textContent = cleanName;
  selectionTag.hidden = false;
  document.querySelector('#loadScore').textContent = 'EN ATTENTE';
  document.querySelector('#loadBar').style.width = '18%';
  document.querySelector('#loadExplanation').textContent = 'La structure est identifiée. ATLAS attend les données du patient et la charge récente pour calculer un indicateur personnalisé.';
    updateLoadUI(patientContext);
  document.querySelector('#recommendationText').textContent = contextualAdvice(rawName, layer);
  ['focusButton', 'isolateButton', 'painButton', 'analyseButton'].forEach((id) => document.querySelector(`#${id}`).disabled = false);
}

function clearSelectionUI() {
  document.querySelector('#emptySelection').hidden = false;
  document.querySelector('#selectedContent').hidden = true;
  selectionTag.hidden = true;
  ['focusButton', 'isolateButton', 'painButton', 'analyseButton'].forEach((id) => document.querySelector(`#${id}`).disabled = true);
}

function focusSelected() { if (selected) fitBox(new THREE.Box3().setFromObject(selected), 3.5); }

function toggleIsolation() {
  if (!selected) return;
  isolated = !isolated;
  pickable.forEach((object) => {
    object.visible = isolated ? object === selected : true;
  });
  if (!isolated) Object.entries(LAYERS).forEach(([key, data]) => { const group = loadedLayers.get(key); if (group) group.visible = data.visible; });
  document.querySelector('#isolateButton span').textContent = isolated ? 'Tout afficher' : 'Isoler';
  if (isolated) focusSelected(); else fitWholeModel();
}

function restoreView() {
  if (selected) restoreMaterial(selected);
  selected = null; hovered = null; isolated = false;
  pickable.forEach((object) => object.visible = true);
  Object.entries(LAYERS).forEach(([key, data]) => {
    data.visible = key !== 'insertions';
    const group = loadedLayers.get(key); if (group) group.visible = data.visible;
    const button = document.querySelector(`[data-layer="${key}"]`);
    button?.classList.toggle('active', data.visible); button?.setAttribute('aria-pressed', String(data.visible));
  });
  document.querySelector('#isolateButton span').textContent = 'Isoler';
  clearSelectionUI(); fitWholeModel();
}

function toggleLayer(button) {
  const key = button.dataset.layer;
  LAYERS[key].visible = !LAYERS[key].visible;
  const group = loadedLayers.get(key); if (group) group.visible = LAYERS[key].visible;
  button.classList.toggle('active', LAYERS[key].visible);
  button.setAttribute('aria-pressed', String(LAYERS[key].visible));
  if (selected?.userData.layer === key && !LAYERS[key].visible) { restoreMaterial(selected); selected = null; clearSelectionUI(); }
}

function showError(message) {
  const banner = document.createElement('div'); banner.className = 'error-banner'; banner.textContent = message; viewport.appendChild(banner);
}

document.querySelectorAll('.layer-button').forEach((button) => button.addEventListener('click', () => toggleLayer(button)));
document.querySelector('#focusButton').addEventListener('click', focusSelected);
document.querySelector('#isolateButton').addEventListener('click', toggleIsolation);
document.querySelector('#restoreButton').addEventListener('click', restoreView);
document.querySelector('#painButton').addEventListener('click', () => alert('La structure sélectionnée sera transmise à la future fiche de douleur ATLAS.'));
document.querySelector('#analyseButton').addEventListener('click', () => alert('Connexion à Atlas Brain prévue dans la prochaine étape.'));
document.querySelector('#dismissHelp').addEventListener('click', () => interactionHelp.remove());
canvas.addEventListener('pointerdown', onPointerDown);
canvas.addEventListener('pointerup', onPointerUp);
canvas.addEventListener('pointermove', onPointerMove);
canvas.addEventListener('pointerleave', () => { if (hovered && hovered !== selected) restoreMaterial(hovered); hovered = null; });
canvas.addEventListener('dblclick', (event) => { setPointer(event); const hit = firstVisibleIntersection(); if (hit) { selectObject(hit); focusSelected(); } });
window.addEventListener('resize', resize);

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

resize(); animate(); loadAnatomy();
