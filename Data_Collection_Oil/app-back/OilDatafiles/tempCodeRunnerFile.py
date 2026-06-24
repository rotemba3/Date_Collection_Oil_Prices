
print(f"  {BIN_EDGES_FILE}  (replaces bin_table.pkl)")
print(f"  {TRAINING_RESULTS_FILE}")
print(f"  {FEATURE_IMPORTANCE_FILE}")

print(f"\nBest model:  {best_model_name}")
print(f"Split:       {best_split}")
print(f"Accuracy:    {best['accuracy']:.4f}")
print(f"F1 macro:    {best['f1_macro']:.4f}")