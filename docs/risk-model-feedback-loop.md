# Risk Model Feedback Loop

Yes. The delay-risk model can start on synthetic logistics data and then retrain on actual learning data collected by the agent over time.

## What Changed

The model still warm-starts with synthetic data in `backend/app/ai_agent/risk_models.py`. Synthetic data is useful at startup because the system may not have enough resolved shipments to train a stable classifier.

After the agent runs, it now collects real examples from `decision_log`:

1. `Detect` builds the eight model features for each shipment.
2. `Act` logs delay-risk decisions and stores the exact feature snapshot in `DecisionLog.evidence.model_features`.
3. `Learn` calls `evaluate_outcomes()` to resolve pending decisions when the shipment outcome is known.
4. Resolved delay-risk decisions become labeled training samples:
   - `success` -> label `0`, the shipment stayed within SLA.
   - `failed` -> label `1`, the shipment missed SLA, is projected beyond SLA, or failed.
5. Every configured number of agent cycles, `Learn` attempts to retrain the active `DelayRiskModel` from those resolved samples.

## Why Feature Snapshots Matter

The model must train on the same inputs it saw when it made the prediction. Carrier reliability, route weather, route traffic, and warehouse congestion can change later. Storing `model_features` at decision time prevents retraining on a later state that did not actually produce the original prediction.

## Training Strategy

Retraining uses a hybrid dataset:

- Synthetic samples remain as a backfill.
- Real resolved samples are appended and assigned a higher sample weight.
- The model only retrains after a minimum number of real samples exists.

This avoids two common failures:

- Overfitting to the first few outcomes.
- Losing coverage of rare but important logistics patterns before enough real data has accumulated.

## Configuration

These backend environment variables control the loop:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `RISK_MODEL_RETRAIN_INTERVAL_CYCLES` | `10` | Attempt retraining every N agent cycles. Set `0` to disable. |
| `RISK_MODEL_RETRAIN_MIN_SAMPLES` | `25` | Minimum resolved real samples before retraining. |
| `RISK_MODEL_RETRAIN_SYNTHETIC_SAMPLES` | `2000` | Synthetic samples included during hybrid retraining. |
| `RISK_MODEL_REAL_SAMPLE_WEIGHT` | `4.0` | Weight multiplier for real learning samples. |

## Runtime Visibility

`GET /api/agent/status` now includes `model_training`, for example:

```json
{
  "source": "hybrid",
  "synthetic_samples": 2000,
  "real_samples": 47,
  "accuracy": 0.9123,
  "trained_at": "2026-06-08T12:00:00.000000"
}
```

`source` is `synthetic` after startup training and becomes `hybrid` after retraining with real resolved outcomes.

## Current Limitation

The current loop learns from resolved delay-risk decisions, not from every shipment the model scored. That is enough to create a real feedback loop, but it is not a fully unbiased production training set because low-risk shipments that never generated decisions are not logged as training examples.

For a production-grade version, add a dedicated prediction log table that records every scored shipment, including low-risk predictions, then label those rows when shipment outcomes resolve. That would let the model learn from true positives, false positives, true negatives, and false negatives.
