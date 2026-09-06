"""Compacte l'historique Health Connect sans perdre les mesures utiles.

Les anciennes synchronisations créaient des séries FC chevauchantes dont l'ID
était lié à la fenêtre de lecture. Ce script fusionne ces séries par jour/source,
déduplique les échantillons et conserve tous les autres records par source_id.
Une sauvegarde horodatée est créée avant remplacement.
"""
from __future__ import annotations
import json, shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"atlas-data"/"private"/"health-connect-wellness.json"

def main():
    if not PATH.is_file(): raise SystemExit("health-connect-wellness.json introuvable")
    records=json.loads(PATH.read_text(encoding="utf-8"))
    ordinary={}
    hr=defaultdict(dict)
    for item in records if isinstance(records,list) else []:
        if not isinstance(item,dict): continue
        if item.get("type")!="heart_rate_series":
            key=str(item.get("source_id") or f"{item.get('type')}:{item.get('start_time')}")
            ordinary[key]=item;continue
        source=str(item.get("source_device") or "unknown")
        for sample in item.get("samples",[]):
            if not isinstance(sample,dict): continue
            ts=str(sample.get("timestamp") or "")
            if not ts: continue
            day=ts[:10];value=sample.get("value")
            hr[(source,day)][(ts,value)]={"timestamp":ts,"value":value}
    compact=list(ordinary.values())
    for (source,day),samples in sorted(hr.items()):
        ordered=sorted(samples.values(),key=lambda x:x["timestamp"])
        for index in range(0,len(ordered),5000):
            chunk=ordered[index:index+5000]
            if not chunk: continue
            compact.append({"source_id":f"heart-rate:{source}:{day}:{index//5000}","type":"heart_rate_series","start_time":chunk[0]["timestamp"],"end_time":chunk[-1]["timestamp"],"local_day":day,"source_device":source,"samples":chunk})
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    backup=PATH.with_name(f"health-connect-wellness.backup-before-compact-{stamp}.json")
    shutil.copy2(PATH,backup)
    tmp=PATH.with_suffix(".json.compact.tmp")
    tmp.write_text(json.dumps(compact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(PATH)
    print(f"Avant : {len(records)} records / {backup.stat().st_size/1024/1024:.1f} Mio")
    print(f"Après : {len(compact)} records / {PATH.stat().st_size/1024/1024:.1f} Mio")
    print(f"Sauvegarde : {backup.name}")
if __name__=="__main__": main()
