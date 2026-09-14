"""
Inference engine for the rule-based half of the expert system.

Technique: forward-chaining production rules + Certainty Factor (CF)
algebra (the classic MYCIN-style approach) for uncertainty handling.

Why CFs: farmers rarely report a "complete" symptom picture, several
different problems share overlapping symptoms, and the knowledge itself
is heuristic rather than exact -- CFs let the engine express "fairly
confident" instead of forcing a hard yes/no.
"""
from collections import defaultdict
from .models import Rule


def _match_strength(observed: set, required: set) -> float:
    """
    Partial matching: what fraction of a rule's required symptoms were
    actually observed. This is the heuristic that turns an incomplete
    symptom report into a graded (fuzzy-ish) match rather than an
    all-or-nothing rule fire.
    """
    if not required:
        return 0.0
    overlap = observed & required
    return len(overlap) / len(required)


def combine_cf(cf1: float, cf2: float) -> float:
    """
    Standard certainty-factor combination for two pieces of evidence
    pointing at the same conclusion (both positive):
        CF_combined = cf1 + cf2 * (1 - cf1)
    This is how the engine fuses multiple rules that independently
    support the same diagnosis, without simply averaging them away.
    """
    return cf1 + cf2 * (1 - cf1)


MIN_MATCH_STRENGTH = 0.34  # a rule must have at least ~1/3 of its symptoms observed to fire


def diagnose(crop: str, observed_symptoms: list[str]) -> list[dict]:
    """
    Forward-chain over all rules applicable to `crop` (plus generic
    'general' rules), fire the ones whose symptom pattern sufficiently
    matches what was observed, combine evidence per conclusion, and
    return a ranked list of {rule_id, conclusion, cf, advice, matched}.
    """
    observed = set(observed_symptoms)
    candidate_rules = Rule.objects.filter(crop__in=[crop, "general"])

    per_conclusion_cf = {}
    per_conclusion_meta = defaultdict(list)

    for rule in candidate_rules:
        required = set(rule.symptoms)
        strength = _match_strength(observed, required)
        if strength < MIN_MATCH_STRENGTH:
            continue

        # Effective CF = expert's base confidence scaled by how complete
        # the observed evidence is for this specific rule.
        effective_cf = round(rule.base_cf * strength, 4)

        prev = per_conclusion_cf.get(rule.conclusion, 0.0)
        per_conclusion_cf[rule.conclusion] = round(combine_cf(prev, effective_cf), 4)
        per_conclusion_meta[rule.conclusion].append({
            "rule_id": rule.id,
            "advice": rule.advice,
            "matched_symptoms": sorted(observed & required),
            "match_strength": round(strength, 2),
        })

    results = []
    for conclusion, cf in per_conclusion_cf.items():
        meta_list = per_conclusion_meta[conclusion]
        # Attribute the result to whichever contributing rule fired strongest,
        # so feedback can be tied back to a specific rule for adaptation.
        best_rule_meta = max(meta_list, key=lambda m: m["match_strength"])
        results.append({
            "rule_id": best_rule_meta["rule_id"],
            "conclusion": conclusion,
            "cf": cf,
            "confidence_pct": round(cf * 100, 1),
            "advice": best_rule_meta["advice"],
            "matched_symptoms": best_rule_meta["matched_symptoms"],
            "supporting_rules": len(meta_list),
        })

    results.sort(key=lambda r: r["cf"], reverse=True)
    return results


LEARNING_RATE = 0.15


def adapt_rule_confidence(rule: Rule, is_correct: bool) -> float:
    """
    Data-driven adaptive component (rule side).

    Every time a farmer confirms or rejects a diagnosis, we nudge that
    rule's base_cf towards 1.0 (confirmed) or 0.0 (rejected) using an
    exponential-moving-average update:

        new_cf = old_cf + LEARNING_RATE * (target - old_cf)

    This lets frequently-confirmed rules become more trusted over time
    and frequently-wrong rules fade out, without needing to retrain a
    full model -- appropriate for a small, interpretable rule base.
    """
    target = 1.0 if is_correct else 0.0
    new_cf = rule.base_cf + LEARNING_RATE * (target - rule.base_cf)
    rule.base_cf = round(max(0.05, min(0.99, new_cf)), 4)
    if is_correct:
        rule.times_confirmed += 1
    else:
        rule.times_rejected += 1
    rule.save(update_fields=["base_cf", "times_confirmed", "times_rejected", "updated_at"])
    return rule.base_cf
