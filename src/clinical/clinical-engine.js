// ╔════════════════════════════════════════════════════════════════╗
// ║ ATLAS OS — Clinical Reasoning Engine — Genesis 0.3.0          ║
// ╚════════════════════════════════════════════════════════════════╝
"use strict";
(() => {
    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION ET STRUCTURES
    // ████████████████████████████████████████████████████████████
    const VERSION="0.3.0";
    const CATEGORIES=Object.freeze(["symptom","profession","sport","sleep","stress","nutrition","environment","history","mobility","strength","recovery","goal"]);
    const id=()=>crypto?.randomUUID?.()||`atlas-clinical-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const now=()=>new Date().toISOString();
    const clone=v=>typeof structuredClone==="function"?structuredClone(v):JSON.parse(JSON.stringify(v));
    const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
    const createCase=(data={})=>({meta:{id:id(),version:VERSION,createdAt:now(),updatedAt:now()},personId:String(data.personId||""),reasonForConsultation:String(data.reasonForConsultation||""),symptoms:[],factors:[],hypotheses:[],recommendations:[],redFlags:[],education:[]});
    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — ANAMNÈSE ET FACTEURS
    // ████████████████████████████████████████████████████████████
    const valid=c=>Boolean(c?.meta?.id&&Array.isArray(c.symptoms)&&Array.isArray(c.factors)&&Array.isArray(c.hypotheses));
    const assert=c=>{if(!valid(c))throw new TypeError("Atlas Clinical : dossier invalide.");};
    const touch=c=>{c.meta.version=VERSION;c.meta.updatedAt=now();};
    function addFactor(c,f={}){assert(c);const x={id:id(),category:CATEGORIES.includes(String(f.category))?String(f.category):"history",label:String(f.label||"Facteur"),description:String(f.description||""),direction:f.direction==="protective"?"protective":"risk",weight:clamp(Number(f.weight)||0,0,100),source:String(f.source||"anamnesis"),observedAt:f.observedAt||now()};c.factors.push(x);touch(c);return clone(x);}
    function addSymptom(c,s={}){assert(c);const x={id:id(),region:String(s.region||"non précisée"),side:String(s.side||"non précisé"),intensity:clamp(Number(s.intensity)||0,0,10),duration:String(s.duration||""),description:String(s.description||""),recordedAt:now()};c.symptoms.push(x);touch(c);return clone(x);}
    // ████████████████████████████████████████████████████████████
    // 🟨 FIN PARTIE C — C01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — HYPOTHÈSES EXPLICABLES
    // ████████████████████████████████████████████████████████████
    function confidence(c,support=[],contradict=[]){assert(c);const sum=ids=>c.factors.filter(f=>ids.includes(f.id)).reduce((t,f)=>t+f.weight,0);const score=clamp(Math.round(35+sum(support)*.45-sum(contradict)*.35+Math.min(20,(support.length+contradict.length)*4)),0,100);return{score,level:score>=90?"very-high":score>=75?"high":score>=55?"moderate":score>=35?"low":"very-low",evidenceCount:support.length+contradict.length};}
    function createHypothesis(c,h={}){assert(c);const support=Array.isArray(h.supportingFactorIds)?h.supportingFactorIds:[];const contradict=Array.isArray(h.contradictingFactorIds)?h.contradictingFactorIds:[];const x={id:id(),title:String(h.title||"Hypothèse clinique"),explanation:String(h.explanation||""),supportingFactorIds:clone(support),contradictingFactorIds:clone(contradict),confidence:confidence(c,support,contradict),status:"open",createdAt:now()};c.hypotheses.push(x);touch(c);return clone(x);}
    // ████████████████████████████████████████████████████████████
    // 🟧 FIN PARTIE D — D01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // 🟪 PARTIE E — E01 — ORIENTATION ET ÉDUCATION
    // ████████████████████████████████████████████████████████████
    function addRecommendation(c,r={}){assert(c);const x={id:id(),category:String(r.category||"education"),title:String(r.title||"Recommandation"),explanation:String(r.explanation||""),priority:clamp(Number(r.priority)||1,1,5),createdAt:now()};c.recommendations.push(x);touch(c);return clone(x);}
    function summary(c){assert(c);const sorted=[...c.hypotheses].sort((a,b)=>b.confidence.score-a.confidence.score);return{caseId:c.meta.id,reasonForConsultation:c.reasonForConsultation,symptomCount:c.symptoms.length,factorCount:c.factors.length,hypothesisCount:c.hypotheses.length,recommendationCount:c.recommendations.length,leadingHypothesis:sorted[0]||null,requiresProfessionalAssessment:c.redFlags.length>0,updatedAt:c.meta.updatedAt};}
    // ████████████████████████████████████████████████████████████
    // 🟪 FIN PARTIE E — E01
    // ████████████████████████████████████████████████████████████

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — API PUBLIQUE
    // ████████████████████████████████████████████████████████████
    window.AtlasClinical=Object.freeze({VERSION,CATEGORIES,createCase,addFactor,addSymptom,createHypothesis,calculateConfidence:confidence,addRecommendation,buildClinicalSummary:summary,isValidCase:valid});
    console.info(`Atlas Clinical Engine ${VERSION} chargé.`);
    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████
})();
