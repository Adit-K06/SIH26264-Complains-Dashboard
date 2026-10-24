import pandas as pd
from app.ai.institution_resolver import normalize_name, resolve_institution

def test_exact_aicte_id_wins():
    df=pd.DataFrame([{"institution_id":7,"institution_name":"ABC College of Engineering","aicte_id":"ID-7"}])
    result=resolve_institution(df,"wrong name","ID-7")
    assert result.institution_id==7 and result.method=="EXACT_ID" and result.confidence==1.0

def test_messy_name_auto_matches():
    df=pd.DataFrame([{"institution_id":7,"institution_name":"ABC College of Engineering","aicte_id":"ID-7"}])
    result=resolve_institution(df,"ABC Coll. of Engg",None)
    assert result.institution_id==7 and result.method=="FUZZY" and not result.needs_review

def test_ambiguous_names_need_review():
    df=pd.DataFrame([{"institution_id":1,"institution_name":"ABC College of Engineering"},{"institution_id":2,"institution_name":"ABC College of Engineering"}])
    result=resolve_institution(df,"ABC College of Engineering")
    assert result.institution_id is None and result.needs_review and len(result.candidates)>=2

def test_unknown_name_does_not_match():
    df=pd.DataFrame([{"institution_id":1,"institution_name":"ABC College of Engineering"}])
    result=resolve_institution(df,"Completely Different University")
    assert result.method=="NONE" and result.institution_id is None

def test_normalization_aliases():
    assert normalize_name("ABC Engg Coll.")=="abc engineering college"
