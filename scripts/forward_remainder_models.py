"""Re-fit exact accepted E3/E4 selections; compare on frozen populations."""
import json,sys,platform,importlib.metadata
from pathlib import Path
import numpy as np
from scripts import run_fep_e3_r1 as e3
from scripts.full_chain_repair_io import ROOT,write,binding
from workbench_analysis.fep_e3 import models as m
from workbench_analysis.fep_e4 import challenger as c
P='reports/forward_r2_remainder_consolidated_20261007/'
def run():
    versions={k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','threadpoolctl','joblib')}
    cp=e3.contract();assert versions==cp['runtime']
    write(P+'IA06_MODEL_RUNTIME_MANIFEST.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),versions=versions,accepted_runtime=cp['runtime'],threads=2,random_seed=20261005,protocols=[binding('config/fep_e3_experiment_protocol_v1_1.json'),binding('config/fep_e4_challenger_protocol_v1.json')],install_source='E:/codex_tmp/fep_e3_deps',model_formulas_modified=False))
    folds=e3.folds();train=folds['TRAIN'];ids=[r['observation_id'] for r in train]
    deps=e3.load(e3.REPORT/'PRETEST_DEPENDENCIES.json');prep=e3.load(ROOT/deps['preprocessing']['path']);manifest=e3.load(e3.REPORT/'FEATURE_MANIFEST.json')
    rebuilt=m.preprocessing(train,manifest,ids)
    assert all(rebuilt[k]==prep[k] for k in rebuilt if k!='logical_digest')
    result=[]
    for stage,selection in [('E3',deps),('E4',e3.load(ROOT/'reports/fep_e4_r1/SELECTED_DEPENDENCIES.json'))]:
        for name,selected in selection['selected'].items():
            old=e3.load(ROOT/selected['artifact']['path']);fit=m.fit if stage=='E3' else c.fit
            model=fit(train,prep,old['family'],old['parameters'],old['dependencies'],ids)
            predict=m.predict if stage=='E3' else c.predict
            checks={}
            for part,rows in folds.items():
                a=predict(old,rows,prep);b=predict(model,rows,prep)
                delta=float(np.max(np.abs(a-b)));assert delta<=1e-12,(stage,name,part,delta)
                checks[part]=dict(rows=len(rows),max_abs_delta=delta,exact_equal=bool(np.array_equal(a,b)))
            restored=json.loads(json.dumps(model));assert np.array_equal(predict(model,train,prep),predict(restored,train,prep))
            result.append(dict(stage=stage,selection=name,source=selected['artifact'],parameters=old['parameters'],checks=checks,serialization_parity=True,tree_sklearn_delta=model.get('TRAIN_serialization_max_abs_delta')))
            print(stage,name,'fit and parity PASS',flush=True)
    write(P+'IA06_E3_E4_PARITY_RECEIPT.json',dict(status='PASS',preprocessing_exact=True,accepted_rows=binding('reports/fep_e3_r1/EXACT_MODEL_ROWS.jsonl.gz'),fold_manifest=binding('reports/fep_e3_r1/FOLD_MANIFEST.json'),cases=result,production=False,REAL_OOS=False,CHAMPION=False))
if __name__=='__main__':run()
