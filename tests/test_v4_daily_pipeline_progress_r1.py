from datetime import datetime, timezone

from workbench_analysis.v4_daily_pipeline_progress_r1 import InstrumentedProgress, instrument_progress


def test_existing_progress_callback_receives_checkpoint_and_row_count_metrics():
    ticks=iter([10.0,12.25,14.0])
    dates=iter([datetime(2026,10,16,7,0,tzinfo=timezone.utc)]*3)
    events=[]
    timer=InstrumentedProgress(lambda *args:events.append(args),clock=lambda:next(ticks),utc_now=lambda:next(dates))
    timer("2026-10-16","SOURCE_READY",{"status":"READY","row_count":5100})
    timer("2026-10-16","DERIVING",{"security_count":5100})
    timer("2026-10-16","OWNER_BUILD",{"processed_count":5100,"cache_hits":4800})
    assert events[0][2]["progress_contract_id"]=="V4_DAILY_PIPELINE_PROGRESS_R1"
    assert events[0][2]["row_count"]==5100
    assert events[1][2]["since_previous_checkpoint_ms"]==2250.0
    assert events[1][2]["previous_checkpoint_stage"]=="SOURCE_READY"
    assert events[2][2]["stage_elapsed_ms"]==0.0
    assert events[2][2]["duration_scope"]=="CHECKPOINT_INTERVAL_NOT_ISOLATED_STAGE_BENCHMARK"


def test_instrumentation_is_idempotent_and_does_not_wrap_twice():
    timer=InstrumentedProgress(lambda *_:None,clock=lambda:1.0)
    assert instrument_progress(timer) is timer

