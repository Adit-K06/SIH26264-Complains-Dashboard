"""Create deterministic, explicitly synthetic SIH26264 training/evaluation data."""
import random
from datetime import datetime, timedelta
import pandas as pd

from .paths import data_dir

SEED = 42
INSTITUTION_COUNT = 600
COMPLAINT_COUNT = 6000
# Fixed anchor so the dataset is byte-for-byte reproducible (it used datetime.now()).
ANCHOR = datetime(2026, 10, 24, 12, 0, 0)
BUREAUS = ["RB", "PGRC", "APPROVAL", "ACADEMIC", "FINANCE"]
CATEGORIES = ["fee refund", "faculty salary", "infrastructure", "affiliation/approval", "ragging", "admission irregularity", "fake documents"]
OPEN_STATUSES = ["PENDING", "UNDER_PROCESS", "ESCALATED", "TRANSFERRED"]
ALL_STATUSES = OPEN_STATUSES + ["DISPOSED"]
KINDS = ["College of Engineering", "Institute of Technology", "Government Polytechnic", "Institute of Management", "College of Arts and Science"]
STATES = ["Karnataka", "Maharashtra", "Tamil Nadu", "Delhi"]
TEMPLATES = {
"fee refund":["Students report that the institution has not returned their fees.","A complaint alleges an unresolved delay in refunding student fees.","Tuition reimbursement remains pending despite repeated requests.","A student disputes an unexplained deduction from a scholarship.","The complainant asks about a hostel deposit refund."],
"faculty salary":["Teaching staff allege that their salaries have not been paid on time.","Faculty members report outstanding salary payments.","Lecturers claim several months of wages remain unpaid.","A staff member disputes provident fund deductions.","A teacher asks for an experience certificate."],
"infrastructure":["Students raise concerns about unsafe and inadequate campus facilities.","The complaint reports poor maintenance of institutional infrastructure.","A laboratory reportedly has damaged equipment and unsafe wiring.","Students request more drinking water facilities.","The campus road floods during heavy rain."],
"affiliation/approval":["The institution's affiliation or approval documentation is disputed.","A complaint requests verification of the institution's approval status.","Students question whether the programme has valid approval.","The college requests clarification about an inspection date.","A student disputes a transfer certificate entry."],
"ragging":["A student reports an alleged ragging incident on campus.","The complaint alleges harassment of a student by other students.","A student reports intimidation by seniors in the hostel.","A student requests a room change due to a roommate dispute.","A student reports a lost identity card."],
"admission irregularity":["The complaint alleges irregularities in the admission process.","A student disputes the institution's handling of admissions.","Admission records reportedly differ from the published selection list.","A candidate asks for the status of an application.","A student requests correction of a spelling error."],
"fake documents":["The complaint alleges the use of forged academic documents.","Documents submitted by the institution are alleged to be inauthentic.","An investigation is requested into suspected forged certificates.","A student requests a duplicate marks card.","The complainant disputes the date printed on a receipt."],
}

def generate_institutions(rng):
    return pd.DataFrame([{"institution_id":f"SYN-{i:05d}","institution_name":f"Demo {rng.choice(KINDS)} {i}","state":rng.choice(STATES),"aicte_id":f"SYN-AICTE-{i:05d}","source":"SYNTHETIC","is_synthetic":True} for i in range(1, INSTITUTION_COUNT+1)])

def generate_complaints(institutions, rng):
    now = ANCHOR; start = now - timedelta(days=548)
    cases=[]; labels=[]; n=1
    def add(inst, cat, bureau, status, summary, created, group="", complainant=""):
        nonlocal n
        cid=f"SYN-CASE-{n:06d}"; n+=1
        row={"case_id":cid,"case_no":cid,"institution_id":inst["institution_id"],"institution_name":inst["institution_name"],"bureau":bureau,"category":cat,"status":status,"summary":summary,"complaint_text":summary,"complainant_ref":complainant,"created_at":created.isoformat(),"group_id":group,"source":"SYNTHETIC","is_synthetic":True}
        cases.append(row); return row
    def pair(a,b,y,reason,g=""):
        labels.append({"case_a_ref":a["case_id"],"case_b_ref":b["case_id"],"label":y,"reason":reason,"group_id":g})
    # Positive overlaps: same institution/issue, different bureau, open, shared reference.
    for i in range(1,121):
        inst=institutions.iloc[(i-1)%len(institutions)]; cat=CATEGORIES[(i-1)%len(CATEGORIES)]; d=start+timedelta(days=rng.randint(0,500)); g=f"OVERLAP-{i:04d}"; ref=f"SYN-COMP-{i:04d}"; t=TEMPLATES[cat]
        a=add(inst,cat,BUREAUS[i%5],rng.choice(OPEN_STATUSES),t[0],d,g,ref)
        b=add(inst,cat,BUREAUS[(i+1)%5],rng.choice(OPEN_STATUSES),t[1],d+timedelta(days=rng.randint(0,20)),g,ref)
        pair(a,b,1,"PLANTED_CROSS_BUREAU_OVERLAP",g)
    # More subtle positive pairs with no shared complainant reference.
    for i in range(1,61):
        inst=institutions.iloc[(i+200)%len(institutions)]; cat=CATEGORIES[(i*3)%len(CATEGORIES)]; d=start+timedelta(days=rng.randint(0,500)); g=f"NEAR-DUP-{i:04d}"; t=TEMPLATES[cat]
        a=add(inst,cat,BUREAUS[i%5],"PENDING",t[0],d,g)
        b=add(inst,cat,BUREAUS[(i+1)%5],"UNDER_PROCESS",t[2],d+timedelta(days=rng.randint(0,25)),g)
        pair(a,b,1,"PLANTED_NEAR_DUPLICATE",g)
    while n <= COMPLAINT_COUNT:
        inst=institutions.iloc[rng.randrange(len(institutions))]; cat=rng.choice(CATEGORIES); summary=rng.choice(TEMPLATES[cat]); d=start+timedelta(seconds=rng.randint(0,int((now-start).total_seconds())))
        if rng.random()<.4: summary += f" Reference {rng.randint(1000,9999)} was included in the submission."
        add(inst,cat,rng.choice(BUREAUS),rng.choice(ALL_STATUSES),summary,d)
    frame=pd.DataFrame(cases)
    # Hard negatives deliberately overlap on some features; never label a planted positive pair negative.
    used={tuple(sorted((x['case_a_ref'],x['case_b_ref']))) for x in labels}; negative=0; attempts=0
    while negative<240 and attempts<20000:
        attempts+=1; a=frame.iloc[rng.randrange(len(frame))]; mode=negative%4
        if mode==0:
            cand=frame[(frame.institution_id==a.institution_id)&(frame.category==a.category)&(frame.case_id!=a.case_id)&(frame.bureau!=a.bureau)&(frame.complainant_ref!=a.complainant_ref)]
            reason="SAME_INSTITUTION_SIMILAR_CATEGORY_DIFFERENT_CASE"
        elif mode==1:
            cand=frame[(frame.institution_id!=a.institution_id)&(frame.category==a.category)&(frame.bureau!=a.bureau)&(frame.case_id!=a.case_id)]
            reason="SIMILAR_ISSUE_DIFFERENT_INSTITUTION"
        elif mode==2:
            cand=frame[(frame.institution_id==a.institution_id)&(frame.category==a.category)&(frame.status=="DISPOSED")&(frame.case_id!=a.case_id)]
            reason="DISPOSED_CASE"
        else:
            cand=frame[(frame.bureau==a.bureau)&(frame.case_id!=a.case_id)]
            reason="SAME_BUREAU"
        if cand.empty: continue
        b=cand.iloc[rng.randrange(len(cand))]; key=tuple(sorted((a.case_id,b.case_id)))
        if key in used: continue
        used.add(key); pair(a.to_dict(),b.to_dict(),0,reason,f"NEG-{negative+1:04d}"); negative+=1
    messy=[]
    for i in range(100):
        inst=institutions.iloc[i]; original=inst.institution_name; variant=original.replace("Institute","Inst.").replace("College","Coll.")
        if i%3==0: variant=variant.lower()
        elif i%3==1: variant=variant.replace(" of "," ")
        messy.append({"institution_id":inst.institution_id,"original_name":original,"messy_name":variant,"aicte_id":"" if i%2==0 else inst.aicte_id,"source":"SYNTHETIC"})
    return frame, pd.DataFrame(labels), pd.DataFrame(messy)

def main():
    rng=random.Random(SEED); DATA_DIR=data_dir(); DATA_DIR.mkdir(parents=True,exist_ok=True); inst=generate_institutions(rng); cases,labels,messy=generate_complaints(inst,rng)
    inst.to_csv(DATA_DIR/"institutions.csv",index=False); cases.to_csv(DATA_DIR/"complaints.csv",index=False); labels.to_csv(DATA_DIR/"labels.csv",index=False); messy.to_csv(DATA_DIR/"messy_institution_names.csv",index=False)
    print(f"Synthetic data generated: {len(inst)} institutions, {len(cases)} cases, {sum(labels.label==1)} positive pairs, {sum(labels.label==0)} negative pairs, {len(messy)} messy names.")
    print(f"Written to {DATA_DIR}. All records are synthetic; not real AICTE data.")
if __name__=="__main__": main()
