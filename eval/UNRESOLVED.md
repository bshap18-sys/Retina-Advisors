## Prompt gaps (non-must-pass scenarios)

Scenario 5: delivery_to_dispute_days field not reliably reaching synthesis - fix is already written and approved but not committed
Scenarios 6 and 7: subscription_canceled pipeline classification label fix written and approved but not committed
Scenarios 1 and 2: confidence calibration - model returns Medium on clear friendly fraud, accepted as variance for now but could be tightened further

## Eval infrastructure

Full 26-scenario run never completed - only 8 of 26 ran before credit exhaustion
Three fixes written during session (subscription pipeline, delivery_to_dispute_days, scenarios.py signal updates) were not committed because we stopped

## Grader

Quality grader occasionally flags legitimate citations as hallucinations even with Sonnet - adding more fields to _build_quality_slice() may be needed for other scenarios
