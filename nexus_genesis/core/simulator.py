import datetime
import os

try:
    import pandas as pd
    import dowhy
    from dowhy import CausalModel
    import matplotlib.pyplot as plt
    SIMULATOR_AVAILABLE = True
except ImportError:
    SIMULATOR_AVAILABLE = False
    print("--- [ CAUSAL BRAIN: dowhy not available — simulator disabled ] ---")

class WorldSimulator:
    def __init__(self):
        if SIMULATOR_AVAILABLE:
            print("--- [ CAUSAL BRAIN: WORLD SIMULATOR ONLINE ] ---")
        else:
            print("--- [ CAUSAL BRAIN: SIMULATOR DISABLED (dowhy not installed) ] ---")

    def run_simulation(self, data_dict, treatment, outcome, common_causes):
        if not SIMULATOR_AVAILABLE:
            return {"status": "disabled", "reason": "dowhy not installed"}
        try:
            df = pd.DataFrame(data_dict)

            # 1. Model the causal graph
            model = CausalModel(
                data=df,
                treatment=treatment,
                outcome=outcome,
                common_causes=common_causes
            )

            # 2. Identify and Estimate
            identified_estimand = model.identify_effect(proceed_when_unidentified=True)
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression"
            )

            # --- VISUALIZATION: Save causal distribution PNG ---
            plt.figure(figsize=(10, 6))

            # Plot the raw data points
            plt.scatter(df[treatment], df[outcome], alpha=0.4, color='#1f77b4', label='Observations')

            # Plot the causal trend line
            plt.plot(df[treatment], estimate.value * df[treatment], color='#d62728', linewidth=2, label='Causal Trend')

            plt.title(f"Causal Impact: {treatment} → {outcome}", fontsize=14)
            plt.xlabel(treatment, fontsize=12)
            plt.ylabel(outcome, fontsize=12)
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.6)

            # Save the evidence plot
            if not os.path.exists("output/plots"):
                os.makedirs("output/plots")

            plot_fn = f"output/plots/sim_{datetime.datetime.now().strftime('%H%M%S')}.png"
            plt.savefig(plot_fn)
            plt.close()

            return {
                "causal_estimate": estimate.value,
                "summary": f"Changing {treatment} results in a {estimate.value:.4f} change in {outcome}.",
                "plot_path": plot_fn
            }
        except Exception as e:
            return {"error": str(e)}