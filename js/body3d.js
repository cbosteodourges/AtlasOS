/*=========================================
 ATLAS OS - Body3D V1
=========================================*/

const container = document.getElementById("viewer3D");

if (container && window.THREE) {

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
45,
container.clientWidth / container.clientHeight,
0.1,
1000
);

camera.position.z = 4;

const renderer = new THREE.WebGLRenderer({
alpha:true,
antialias:true
});

renderer.setSize(
container.clientWidth,
container.clientHeight
);

container.appendChild(renderer.domElement);

// Lumière

const light = new THREE.PointLight(0x66ccff,2);

light.position.set(5,5,5);

scene.add(light);

const ambient = new THREE.AmbientLight(0xffffff,.7);

scene.add(ambient);

// Silhouette temporaire

const geometry = new THREE.IcosahedronGeometry(1,4);

const material = new THREE.MeshPhysicalMaterial({

color:0x38BDF8,

metalness:.15,

roughness:.2,

transmission:.2,

transparent:true,

opacity:.95

});

const body = new THREE.Mesh(
geometry,
material
);

scene.add(body);

// Halo

const ring = new THREE.Mesh(

new THREE.TorusGeometry(1.6,.02,16,120),

new THREE.MeshBasicMaterial({

color:0x38BDF8

})

);

scene.add(ring);

function animate(){

requestAnimationFrame(animate);

body.rotation.y+=0.004;

body.rotation.x+=0.001;

ring.rotation.z+=0.002;

renderer.render(scene,camera);

}

animate();

window.addEventListener("resize",()=>{

camera.aspect=

container.clientWidth/container.clientHeight;

camera.updateProjectionMatrix();

renderer.setSize(

container.clientWidth,

container.clientHeight

);

});

}
