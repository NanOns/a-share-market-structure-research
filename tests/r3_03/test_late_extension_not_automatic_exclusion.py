from shadow_v2.breakout_prep import LATE_EXTENSION_IS_NOT_AUTOMATIC_EXCLUSION,classify
def test_warning_not_classifier_input():
 assert LATE_EXTENSION_IS_NOT_AUTOMATIC_EXCLUSION and classify(True,"RANGE_CONTRACTED","VOL_CONTRACTED")[1]
