"""Reproducible held-out evaluation of the Tier-B scorer on synthetic labeled pairs."""
from __future__ import annotations
import json
from pathlib import Path
import hashlib
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from .overlap import OPEN_STATUSES, score_pair, OVERLAP_THRESHOLD

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/"data"; DOCS=ROOT/"docs"

def _partition(inst_id: str) -> str:
    # Stable group-level split; no random state or runtime-dependent ordering.
    n=int(hashlib.sha256(str(inst_id).encode()).hexdigest()[:8],16)%100
    return "test" if n<40 else "train"

def _metric(y, pred):
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel().tolist()
    return {"precision":round(precision_score(y,pred,zero_division=0),4),"recall":round(recall_score(y,pred,zero_division=0),4),"f1":round(f1_score(y,pred,zero_division=0),4),"accuracy":round(accuracy_score(y,pred),4),"confusion_matrix":{"true_negative":tn,"false_positive":fp,"false_negative":fn,"true_positive":tp},"support":len(y)}

def _eligible(a,b):
    return (str(a.get("institution_id"))==str(b.get("institution_id")) and str(a.get("bureau"))!=str(b.get("bureau")) and str(a.get("status","")).upper() in OPEN_STATUSES and str(b.get("status","")).upper() in OPEN_STATUSES)

def main():
    cases=pd.read_csv(DATA/"complaints.csv",keep_default_na=False)
    labels=pd.read_csv(DATA/"labels.csv",keep_default_na=False)
    indexed=cases.set_index("case_id",drop=False)
    records=[]; excluded=0
    for row in labels.to_dict("records"):
        if row["case_a_ref"] not in indexed.index or row["case_b_ref"] not in indexed.index: continue
        a=indexed.loc[row["case_a_ref"]].to_dict(); b=indexed.loc[row["case_b_ref"]].to_dict()
        pa,pb=_partition(a["institution_id"]),_partition(b["institution_id"])
        if pa!=pb: excluded+=1; continue
        part=pa
        # Evaluate the same score_pair formula used by the production detector.
        score=score_pair(a,b)["score"]
        records.append({"label":int(row["label"]),"score":score,"partition":part,"eligible":_eligible(a,b),"reason":row["reason"],"group_id":row.get("group_id","")})
    frame=pd.DataFrame(records)
    train=frame[frame.partition=="train"]; test=frame[frame.partition=="test"]
    if train.empty or test.empty or train.label.nunique()<2 or test.label.nunique()<2:
        raise RuntimeError("Evaluation split needs both positive and negative labels in train and held-out partitions. Regenerate data and retry.")
    thresholds=[round(x/100,2) for x in range(40,91,5)]
    tuned=max(thresholds,key=lambda t:(f1_score(train.label,train.score>=t,zero_division=0),precision_score(train.label,train.score>=t,zero_division=0),t))
    test_metrics=_metric(test.label,(test.score>=tuned).astype(int))
    baseline=((test.score>=0.60)).astype(int)
    # Also report detector-realistic eligible-only metrics; ineligible pairs are not sent to Tier B.
    eligible=test[test.eligible]
    eligible_metrics=_metric(eligible.label,(eligible.score>=tuned).astype(int)) if len(eligible) and eligible.label.nunique()==2 else None
    baseline_eligible=_metric(eligible.label,(eligible.score>=0.60).astype(int)) if len(eligible) and eligible.label.nunique()==2 else None
    output={"synthetic_only":True,"seed":42,"split":"stable institution hash; cross-partition institution pairs excluded","training_pairs":len(train),"held_out_pairs":len(test),"excluded_cross_partition_pairs":excluded,"selected_threshold":tuned,"threshold_search":thresholds,"held_out_metrics":test_metrics,"baseline_threshold_0_60_metrics":_metric(test.label,baseline),"eligible_cross_bureau_open_pairs":len(eligible),"eligible_only_metrics":eligible_metrics,"eligible_only_baseline_metrics":baseline_eligible,"interpretation":"Synthetic metrics validate code paths only. They are not evidence of performance on real AICTE complaints."}
    DOCS.mkdir(parents=True,exist_ok=True)
    (DOCS/"evaluation.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    md=["# Synthetic AI/ML evaluation","","**Warning:** all records are synthetic. These results are not evidence of performance on real AICTE complaints.","",f"- Training pairs: {len(train)}",f"- Held-out pairs: {len(test)}",f"- Excluded cross-partition pairs: {excluded}",f"- Selected threshold: {tuned:.2f}","","## Held-out metrics",""]
    for k,v in test_metrics.items(): md.append(f"- **{k}:** `{json.dumps(v)}`")
    md += ["","## Detector-eligible held-out pairs","",f"- Eligible pairs: {len(eligible)}",f"- Metrics: `{json.dumps(eligible_metrics)}`",f"- Baseline (0.60): `{json.dumps(baseline_eligible)}`","","## Interpretation","","Use these metrics to verify reproducibility and compare algorithm revisions only. Review false positives/negatives and validate against expert-labeled real cases before operational use."]
    (DOCS/"evaluation.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("Synthetic evaluation completed.")
    print(json.dumps({k:output[k] for k in ["training_pairs","held_out_pairs","excluded_cross_partition_pairs","selected_threshold","held_out_metrics","eligible_cross_bureau_open_pairs","eligible_only_metrics"]},indent=2))
    print(f"Reports written to: {DOCS}")
    print("All data and results are synthetic; not real AICTE complaints.")
if __name__=="__main__": main()
