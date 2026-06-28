"""
ExamScanner/report.py
Run this to get all ML metrics for your thesis report.

Usage:
    cd C:\\Users\\rajun\\WebApplication
    python -m app.ExamScanner.report
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ExamScanner.classifier import FieldClassifier, DATA_PATH

print("\n" + "="*56)
print("  ExamScanner — ML Metrics Report")
print("="*56)

clf = FieldClassifier()
m   = clf.train(DATA_PATH, verbose=True)
clf.save()

print("\n" + "-"*56)
print("  SUMMARY (copy into thesis report)")
print("-"*56)
print(f"  Algorithm      : RandomForest (100 trees, max_depth=6)")
print(f"  Features       : 3 (is_digit_string, length_ok, next_token)")
print(f"  Classes        : {m['classes']}")
print(f"  Training samples: {m['n_train']}")
print(f"  Test samples   : {m['n_test']}")
print(f"  Accuracy       : {m['accuracy']*100:.1f}%")
print(f"  CV Accuracy    : {m['cv_mean']*100:.1f}%  (5-fold cross-validation)")
print(f"  Precision      : {m['precision']*100:.1f}%  (weighted)")
print(f"  Recall         : {m['recall']*100:.1f}%  (weighted)")
print(f"  F1 Score       : {m['f1_score']*100:.1f}%  (weighted)")

print("\n  Confusion matrix:")
labels = m['classes']
header = "".join(f"{l[:10]:>12}" for l in labels)
print(f"  {'':>14}{header}")
for i, row in enumerate(m['confusion_matrix']):
    vals = "".join(f"{v:>12}" for v in row)
    print(f"  {labels[i]:>14}{vals}")

print("\n  Per-class results:")
rpt = m['classification_report']
for label in labels:
    r = rpt.get(label, {})
    print(f"    {label:<14}  "
          f"P={r.get('precision',0):.2f}  "
          f"R={r.get('recall',0):.2f}  "
          f"F1={r.get('f1-score',0):.2f}  "
          f"n={int(r.get('support',0))}")
print("="*56 + "\n")

if __name__ == "__main__":
    pass