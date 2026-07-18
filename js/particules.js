/*=========================================
 ATLAS OS - Particles Engine V1
=========================================*/

const canvas = document.getElementById("particles");

if(canvas){

const ctx = canvas.getContext("2d");

let width;
let height;

function resize(){

width = canvas.width = window.innerWidth;

height = canvas.height = window.innerHeight;

}

resize();

window.addEventListener("resize", resize);

const particles=[];

const TOTAL=80;

for(let i=0;i<TOTAL;i++){

particles.push({

x:Math.random()*width,

y:Math.random()*height,

vx:(Math.random()-0.5)*0.3,

vy:(Math.random()-0.5)*0.3,

r:Math.random()*2+1

});

}

function animate(){

ctx.clearRect(0,0,width,height);

particles.forEach(p=>{

p.x+=p.vx;

p.y+=p.vy;

if(p.x<0||p.x>width)p.vx*=-1;
if(p.y<0||p.y>height)p.vy*=-1;

ctx.beginPath();

ctx.arc(p.x,p.y,p.r,0,Math.PI*2);

ctx.fillStyle="rgba(56,189,248,.8)";

ctx.fill();

});

for(let i=0;i<particles.length;i++){

for(let j=i+1;j<particles.length;j++){

const dx=particles[i].x-particles[j].x;
const dy=particles[i].y-particles[j].y;

const d=Math.sqrt(dx*dx+dy*dy);

if(d<140){

ctx.beginPath();

ctx.moveTo(particles[i].x,particles[i].y);

ctx.lineTo(particles[j].x,particles[j].y);

ctx.strokeStyle=`rgba(56,189,248,${0.15-(d/1400)})`;

ctx.stroke();

}

}

}

requestAnimationFrame(animate);

}

animate();

}
