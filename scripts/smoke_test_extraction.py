"""
Quick extraction smoke test — verifies true positives / true negatives.
Run: python scripts/smoke_test_extraction.py
"""
import sys
sys.path.insert(0, '.')

from ml.preprocessing import Sentence
from ml.extraction import analyze_sentences, extract_actions, extract_decisions

POSITIVE_ACTIONS = [
    "I will send the email by Friday.",
    "Can you prepare the slides for the next meeting?",
    "We need to finalize the design by end of week.",
    "I'll just check with the team and get back to you.",
]
NEGATIVE_ACTIONS = [
    "That is interesting.",
    "Okay.",
    "I don't know.",
    "My favorite animal is my dog.",
]

POSITIVE_DECISIONS = [
    "We have decided to use the modular approach.",
    "It was agreed that the selling price will be 25 euros.",
    "We will go with the compact design.",
]
NEGATIVE_DECISIONS = [
    "I think maybe we could do this.",
    "That is the plan.",
    "So we were just discussing the project.",
]

def make_sents(texts):
    return [Sentence(text=t, speaker="Speaker1", meeting_id="smoke") for t in texts]

all_action_texts = POSITIVE_ACTIONS + NEGATIVE_ACTIONS
all_decision_texts = POSITIVE_DECISIONS + NEGATIVE_DECISIONS

action_analyzed = analyze_sentences(make_sents(all_action_texts))
decision_analyzed = analyze_sentences(make_sents(all_decision_texts))

actions = extract_actions(action_analyzed)
decisions = extract_decisions(decision_analyzed)

action_texts = {a["action"].strip().lower() for a in actions}
decision_texts = {d["text"].strip().lower() for d in decisions}

print("=== ACTION ITEM DETECTION ===")
tp = fp = fn = tn = 0
for t in POSITIVE_ACTIONS:
    hit = t.strip().lower() in action_texts
    print(f"  {'TP' if hit else 'FN'} | {t}")
    if hit: tp += 1
    else: fn += 1

for t in NEGATIVE_ACTIONS:
    hit = t.strip().lower() in action_texts
    print(f"  {'FP' if hit else 'TN'} | {t}")
    if hit: fp += 1
    else: tn += 1

prec = tp / (tp+fp) if (tp+fp) else 0
rec  = tp / (tp+fn) if (tp+fn) else 0
f1   = (2*prec*rec/(prec+rec)) if (prec+rec) else 0
print(f"\n  TP={tp} FP={fp} FN={fn} TN={tn}")
print(f"  Precision={prec:.2f}  Recall={rec:.2f}  F1={f1:.2f}")

print("\n=== DECISION DETECTION ===")
tp = fp = fn = tn = 0
for t in POSITIVE_DECISIONS:
    hit = t.strip().lower() in decision_texts
    print(f"  {'TP' if hit else 'FN'} | {t}")
    if hit: tp += 1
    else: fn += 1

for t in NEGATIVE_DECISIONS:
    hit = t.strip().lower() in decision_texts
    print(f"  {'FP' if hit else 'TN'} | {t}")
    if hit: fp += 1
    else: tn += 1

prec = tp / (tp+fp) if (tp+fp) else 0
rec  = tp / (tp+fn) if (tp+fn) else 0
f1   = (2*prec*rec/(prec+rec)) if (prec+rec) else 0
print(f"\n  TP={tp} FP={fp} FN={fn} TN={tn}")
print(f"  Precision={prec:.2f}  Recall={rec:.2f}  F1={f1:.2f}")
