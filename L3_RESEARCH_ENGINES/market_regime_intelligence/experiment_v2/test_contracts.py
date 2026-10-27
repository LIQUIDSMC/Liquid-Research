"""Phase 1 contract-only regression tests; no v1 imports or research data."""

import unittest

try:
    from . import contracts as m
except ImportError:
    import contracts as m


T = "EXCESSIVE_EPISODE_TURNOVER"
P = "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE"
C = "CONFLICTING_DIRECTIONAL_FAILURES"
S = "SEVERE_REGIME_IMBALANCE"
E = "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING"
TERM = "TERMINATE_INSTRUMENT_V1"
F24 = "EVALUATE_24H_FALLBACK"
F1 = "EVALUATE_1H_FALLBACK"


def ev(w="4h", reasons=(), action="PROCEED_TO_STAGE_2", h="VIABLE"):
    return m.WindowGate2Completed(
        "GATE2_COMPLETED",
        m.Gate2Evidence(w, frozenset(reasons), action, h),
    )


def d0(w="4h", c="C1"):
    return m.WindowD0Terminal(
        "D0_TERMINAL", w, "NO_TARGET_OBSERVATION_POPULATION", c
    )


def integrity(w="4h"):
    return m.WindowIntegrityFailure(
        "INTEGRITY_FAILURE", w, "MISSING_PREDECESSOR", "C10"
    )


def history(*entries, h=None):
    return m.InstrumentPathProvenance(tuple(entries), h)


def viable(w, *entries, h):
    return m.PathViable("VIABLE", w, history(*entries, h=h))


def gate_terminal(*entries, h):
    return m.PathGate2Terminal(
        "GATE2_TERMINAL", history(*entries, h=h)
    )


def d0_terminal(*entries, h=None):
    return m.PathD0Terminal(
        "D0_TERMINAL", history(*entries, h=h)
    )


CASES = [
    ("primary_viable", True,
     lambda: viable("4h", ev(), h="VIABLE")),
    ("viable_rejects_d0", False,
     lambda: viable("4h", d0(), h=None)),
    ("unauthorized_24h", False,
     lambda: viable("24h", ev(), ev("24h"),
                    h="VIABLE_AFTER_24H_FALLBACK")),
    ("contradictory_gate2", False,
     lambda: ev(reasons=(S,))),
    ("realized_window_mismatch", False,
     lambda: viable("1h", ev(), h="VIABLE")),
    ("terminal_rejects_viable_h", False,
     lambda: gate_terminal(
         ev(reasons=(S,), action=TERM,
            h="STRUCTURALLY_INSUFFICIENT"), h="VIABLE")),
    ("authorized_24h", True,
     lambda: viable(
         "24h",
         ev(reasons=(T,), action=F24, h="PATHOLOGICALLY_FRAGMENTED"),
         ev("24h"), h="VIABLE_AFTER_24H_FALLBACK")),
    ("authorized_1h", True,
     lambda: viable(
         "1h",
         ev(reasons=(P,), action=F1, h="STRUCTURALLY_INSUFFICIENT"),
         ev("1h"), h="VIABLE_AFTER_1H_FALLBACK")),
    ("missing_authorized_fallback", False,
     lambda: history(
         ev(reasons=(T,), action=F24, h="PATHOLOGICALLY_FRAGMENTED"))),
    ("terminal_fallback_preserves_directional_h", True,
     lambda: gate_terminal(
         ev(reasons=(T,), action=F24, h="PATHOLOGICALLY_FRAGMENTED"),
         ev("24h", reasons=(T,), action=TERM,
            h="PATHOLOGICALLY_FRAGMENTED"),
         h="PATHOLOGICALLY_FRAGMENTED")),
    ("unpaired_conflict", False,
     lambda: ev(reasons=(T, C), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("paired_conflict", True,
     lambda: ev(reasons=(T, P, C), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("d0_c1", True, lambda: d0_terminal(d0(c="C1"))),
    ("d0_c2", True, lambda: d0_terminal(d0(c="C2"))),
    ("d0_rejects_h", False,
     lambda: d0_terminal(d0(), h="VIABLE")),
    ("ordinary_final_eligible", True,
     lambda: (
         m.FinalObservationResolved(
             "RESOLVED", "LRS4_ELIGIBLE"
         ).final_eligible is True
     ) or (_ for _ in ()).throw(ValueError("incorrect flag"))),
    ("integrity_has_no_eligible_flag", False,
     lambda: getattr(
         m.FinalObservationIntegrityFailure(
             "INTEGRITY_FAILURE", "MISSING_D3", "W*=4h"
         ), "final_eligible")),
    ("primary_turnover_must_fallback", False,
     lambda: ev(reasons=(T,), action=TERM,
                h="PATHOLOGICALLY_FRAGMENTED")),
    ("primary_persistence_must_fallback", False,
     lambda: ev(reasons=(P,), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("fallback_turnover_terminates", True,
     lambda: ev("24h", (T,), TERM, "PATHOLOGICALLY_FRAGMENTED")),
    ("fallback_persistence_terminates", True,
     lambda: ev("1h", (P,), TERM, "STRUCTURALLY_INSUFFICIENT")),
    ("structural_dominates_directional", True,
     lambda: ev(reasons=(S, T), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("epistemic_dominates_directional", True,
     lambda: ev(reasons=(E, T), action=TERM,
                h="EPISTEMICALLY_INDETERMINATE")),
    ("structural_dominates_epistemic", True,
     lambda: ev(reasons=(S, E), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("primary_only_cannot_be_24h", False,
     lambda: history(ev("24h"))),
    ("viable_rejects_integrity", False,
     lambda: viable("4h", integrity(), h="VIABLE")),
    ("gate_terminal_rejects_d0", False,
     lambda: gate_terminal(d0(), h=None)),
    ("d0_terminal_rejects_gate2", False,
     lambda: d0_terminal(ev())),
    ("viable_requires_h_path", False,
     lambda: viable("4h", ev(), h=None)),
    ("fallback_after_terminal_primary", False,
     lambda: history(
         ev(reasons=(S,), action=TERM,
            h="STRUCTURALLY_INSUFFICIENT"),
         ev("24h"))),
    ("empty_reasons_terminal_action", False,
     lambda: ev(action=TERM)),
    ("empty_reasons_structural_disposition", False,
     lambda: ev(h="STRUCTURALLY_INSUFFICIENT")),
    ("empty_reasons_directional_disposition", False,
     lambda: ev(h="PATHOLOGICALLY_FRAGMENTED")),
    ("nonempty_reasons_viable_disposition", False,
     lambda: ev(reasons=(T,), action=F24)),
    ("unpaired_derived_conflict_extra", False,
     lambda: ev(reasons=(T, C), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("missing_derived_conflict", False,
     lambda: ev(reasons=(T, P), action=TERM,
                h="STRUCTURALLY_INSUFFICIENT")),
    ("duplicate_primary_window", False,
     lambda: history(ev(), ev())),
    ("duplicate_fallback_excess_entries", False,
     lambda: history(
         ev(reasons=(T,), action=F24,
            h="PATHOLOGICALLY_FRAGMENTED"),
         ev("24h"),
         ev("24h"))),
    ("empty_path_history", False,
     lambda: history()),
    ("three_window_path", False,
     lambda: history(ev(), ev("24h"), ev("1h"))),
]


class Phase1ContractTests(unittest.TestCase):
    pass


def install_case(index, name, expected_accept, factory):
    def test(self):
        if expected_accept:
            factory()
        else:
            with self.assertRaises((ValueError, TypeError, AttributeError)):
                factory()

    test.__name__ = f"test_{index:02d}_{name}"
    setattr(Phase1ContractTests, test.__name__, test)


for index, (name, expected_accept, factory) in enumerate(CASES, 1):
    install_case(index, name, expected_accept, factory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
