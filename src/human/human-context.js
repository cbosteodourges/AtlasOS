// ╔════════════════════════════════════════════════════════════════╗
// ║ ATLAS OS — Human Context Engine — Genesis 0.3.0               ║
// ╚════════════════════════════════════════════════════════════════╝
"use strict";
(() => {
    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONTEXTE HUMAIN
    // ████████████████████████████████████████████████████████████
    const VERSION="0.3.0";
    const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
    function create(d={}){return{version:VERSION,professions:{current:d.professions?.current||null,past:Array.isArray(d.professions?.past)?d.professions.past:[]},dailyLife:{sedentaryHours:Number(d.dailyLife?.sedentaryHours)||0,physicalDemand:Number(d.dailyLife?.physicalDemand)||0,repetitiveTasks:Array.isArray(d.dailyLife?.repetitiveTasks)?d.dailyLife.repetitiveTasks:[]},recovery:{sleepHours:Number(d.recovery?.sleepHours)||null,sleepQuality:Number(d.recovery?.sleepQuality)||null,stressLevel:Number(d.recovery?.stressLevel)||null,hydrationStatus:d.recovery?.hydrationStatus||"unknown"},motivation:{mainGoal:d.motivation?.mainGoal||"",confidence:Number(d.motivation?.confidence)||null,availableDays:Number(d.motivation?.availableDays)||0},environment:{altitude:Number(d.environment?.altitude)||0,climate:d.environment?.climate||"",constraints:Array.isArray(d.environment?.constraints)?d.environment.constraints:[]}};}
    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — DISPONIBILITÉ DU JOUR
    // ████████████████████████████████████████████████████████████
    function readiness(c){const sleep=clamp(Number(c?.recovery?.sleepQuality)||50,0,100);const stress=clamp(Number(c?.recovery?.stressLevel)||50,0,100);const demand=clamp(Number(c?.dailyLife?.physicalDemand)||0,0,100);const motivation=clamp(Number(c?.motivation?.confidence)||50,0,100);const score=Math.round(sleep*.35+(100-stress)*.25+(100-demand)*.20+motivation*.20);return{score,level:score>=75?"ready":score>=55?"adapt":"recover"};}
    // ████████████████████████████████████████████████████████████
    // 🟧 FIN PARTIE D — D01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — API PUBLIQUE
    // ████████████████████████████████████████████████████████████
    window.AtlasHumanContext=Object.freeze({VERSION,create,calculateReadiness:readiness});
    console.info(`Atlas Human Context ${VERSION} chargé.`);
    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████
})();
