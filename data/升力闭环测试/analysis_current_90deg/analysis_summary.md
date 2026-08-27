# 90-degree axial-inflow three-method control analysis

- Parsed 28 logs into 27 method-condition cells and 9 three-method matched conditions.
- Channel 1 is the only active thrust/control channel; inactive zero channels were excluded.
- Each run was aligned by the 10% and 90% crossings of a median-filtered freestream-speed signal.
- The disturbance window spans the 10%-90% speed ramp plus 3 s after the 90% crossing.

## Descriptive result

- Full RMSE hierarchy (model FF + feedback < feedback only < static-map open loop) holds in 9/9 matched conditions.
- After subtracting each run's pre-disturbance mean error, the same incremental-RMSE hierarchy holds in 9/9 conditions.
- Feedback-only median RMSE reduction versus static open loop: 89.7% (range 80.2% to 92.9%).
- Model-FF median RMSE reduction versus feedback only: 62.2% (range 45.7% to 74.3%).
- Feedback-only median peak-error reduction versus static: 85.2%; model-FF median peak-error reduction versus feedback only: 40.1%.
- In feedforward + feedback runs, the median trial-level mean absolute feedback share of total output is 5.7%.
- Static-map runs have a median absolute baseline-to-plateau measured-RPM change of 2.8% (range 1.7% to 4.3%).
- The recorded actuator_outputs.output[0] in static-map runs changes by a median absolute 0.000% from baseline to plateau (maximum 0.000%), confirming that the applied primary actuator command is fixed.

## Replication and inference limits

- Only the 15 N / 1 s feedforward + feedback cell is repeated (trial normalized RMSE values: 5.60%, 5.67%).
- Most cells have n=1, so the values are descriptive and do not support confidence intervals, p-values, or a statistical-superiority claim.
- The 25 N / 1 s feedforward + feedback run is at normalized output >= 0.98 for 56.5% of the disturbance window; 25 N conclusions therefore include actuator-limit effects.
- Static logs still contain changing internal thrust_feedback_out/thrust_control_out fields, but actuator_outputs.output[0] is fixed. Treat the former as computed internal signals, not the applied static command.

## Files

- trial_metrics.csv: one row per ULog.
- condition_metrics.csv: duplicate trials averaged within method-condition cells.
- three_method_comparison.csv: matched three-method values and relative reductions.
- fig9_freestream_ramp.*: representative freestream-ramp curve (single-column).
- fig10_representative_response.*: aligned representative response.
- fig11_condition_summary.*: all-condition RMSE reduction heatmaps.
- fig12_speed_error.*: error over the freestream-speed sweep (single-column).
- fig13_feedforward_mechanism.*: model speed, control decomposition, and freestream consistency check.
