// ╔════════════════════════════════════════════════════════════════╗
// ║ ATLAS OS — Adaptive Training Engine — Genesis 0.3.0           ║
// ╚════════════════════════════════════════════════════════════════╝
"use strict";
(() => {
    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — PROFIL ET CHARGE
    // ████████████████████████████████████████████████████████████
    const VERSION="0.3.0";
    const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
    function createProfile(d={}){return{experienceLevel:d.experienceLevel||"beginner",currentWeeklyVolume:Number(d.currentWeeklyVolume)||0,previousWeeklyVolume:Number(d.previousWeeklyVolume)||0,intensitySessions:Number(d.intensitySessions)||0,strengthSessions:Number(d.strengthSessions)||0,mobilitySessions:Number(d.mobilitySessions)||0,recoveryScore:clamp(Number(d.recoveryScore)||50,0,100),painScore:clamp(Number(d.painScore)||0,0,10),readinessScore:clamp(Number(d.readinessScore)||50,0,100)};}
    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — ADAPTATION ET PROGRESSIVITÉ
    // ████████████████████████████████████████████████████████████
    function progression(p){const current=Math.max(0,p.currentWeeklyVolume),previous=Math.max(0,p.previousWeeklyVolume);if(previous===0)return{percentage:current>0?100:0,status:current>0?"new-load":"stable"};const percentage=Math.round(((current-previous)/previous)*100);return{percentage,status:percentage>15?"high-increase":percentage>8?"moderate-increase":percentage<-20?"large-decrease":"controlled"};}
    function capacity(p){const score=clamp(Math.round(p.recoveryScore*.40+p.readinessScore*.35+Math.min(15,p.strengthSessions*5)+Math.min(10,p.mobilitySessions*3)-p.painScore*7),0,100);return{score,level:score>=75?"progress":score>=55?"maintain":score>=35?"reduce":"recover"};}
    // ████████████████████████████████████████████████████████████
    // 🟧 FIN PARTIE D — D01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟪 PARTIE E — E01 — PLAN D'ADAPTATION
    // ████████████████████████████████████████████████████████████
    function guidance(p){const prog=progression(p),cap=capacity(p),r=[];r.push({type:"endurance",action:prog.status==="high-increase"||cap.level==="reduce"?"reduce":cap.level==="progress"?"progress-gradually":"maintain",explanation:"Le volume et l’intensité doivent rester compatibles avec la capacité d’adaptation."});r.push({type:"strength",action:p.strengthSessions>=2?"maintain":"add",targetSessions:2,explanation:"Le renforcement améliore la tolérance mécanique."});r.push({type:"mobility",action:p.mobilitySessions>=2?"maintain":"add",targetSessions:2,explanation:"La mobilité entretient les amplitudes utiles."});r.push({type:"recovery",action:p.recoveryScore<60?"prioritize":"maintain",explanation:"Sommeil, nutrition, hydratation et stress conditionnent l’adaptation."});if(p.painScore>=7)r.unshift({type:"safety",action:"professional-assessment",explanation:"Une douleur importante nécessite une évaluation professionnelle."});return{version:VERSION,progression:prog,adaptiveCapacity:cap,recommendations:r};}
    // ████████████████████████████████████████████████████████████
    // 🟪 FIN PARTIE E — E01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — API PUBLIQUE
    // ████████████████████████████████████████████████████████████
    window.AtlasAdaptiveTraining=Object.freeze({VERSION,createProfile,calculateVolumeProgression:progression,calculateAdaptiveCapacity:capacity,buildWeeklyGuidance:guidance});
    console.info(`Atlas Adaptive Training ${VERSION} chargé.`);
    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████
})();
