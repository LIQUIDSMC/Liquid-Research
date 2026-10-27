"""Frozen-vocabulary authority contracts for LRS4 Experiment v2.

Phase 1 only. No evaluation, routing, or projection logic.
"""

from dataclasses import dataclass
from typing import Literal, TypeAlias, Union


Window: TypeAlias = Literal["1h", "4h", "24h"]

RegimeState: TypeAlias = Literal["HIGH", "LOW"]

Gate2Reason: TypeAlias = Literal[
    "SEVERE_REGIME_IMBALANCE",
    "EXCESSIVE_REGIME_INELIGIBILITY",
    "EXCESSIVE_INELIGIBILITY_CONCENTRATION",
    "INSUFFICIENT_STATE_EPISODE_SUPPORT",
    "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING",
    "EXCESSIVE_EPISODE_TURNOVER",
    "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE",
    "CONFLICTING_DIRECTIONAL_FAILURES",
]

ResolutionAction: TypeAlias = Literal[
    "PROCEED_TO_STAGE_2",
    "EVALUATE_24H_FALLBACK",
    "EVALUATE_1H_FALLBACK",
    "TERMINATE_INSTRUMENT_V1",
]

WindowDisposition: TypeAlias = Literal[
    "VIABLE",
    "PATHOLOGICALLY_FRAGMENTED",
    "STRUCTURALLY_INSUFFICIENT",
    "EPISTEMICALLY_INDETERMINATE",
]

PathDisposition: TypeAlias = Literal[
    "VIABLE",
    "VIABLE_AFTER_24H_FALLBACK",
    "VIABLE_AFTER_1H_FALLBACK",
    "PATHOLOGICALLY_FRAGMENTED",
    "STRUCTURALLY_INSUFFICIENT",
    "EPISTEMICALLY_INDETERMINATE",
]

D0Provenance: TypeAlias = Literal["C1", "C2"]

FinalObservationDisposition: TypeAlias = Literal[
    "LRS4_SOURCE_HISTORY_INELIGIBLE",
    "LRS4_REGIME_INELIGIBLE",
    "LRS4_ELIGIBLE",
]


def _require_member(name: str, value: str, allowed: tuple[str, ...]) -> None:
    if type(value) is not str or value not in allowed:
        raise ValueError(f"{name}: unsupported value {value!r}")


def _require_nonempty(name: str, value: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name}: nonempty string required")


WINDOWS = ("1h", "4h", "24h")
REASONS = (
    "SEVERE_REGIME_IMBALANCE",
    "EXCESSIVE_REGIME_INELIGIBILITY",
    "EXCESSIVE_INELIGIBILITY_CONCENTRATION",
    "INSUFFICIENT_STATE_EPISODE_SUPPORT",
    "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING",
    "EXCESSIVE_EPISODE_TURNOVER",
    "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE",
    "CONFLICTING_DIRECTIONAL_FAILURES",
)
ACTIONS = (
    "PROCEED_TO_STAGE_2",
    "EVALUATE_24H_FALLBACK",
    "EVALUATE_1H_FALLBACK",
    "TERMINATE_INSTRUMENT_V1",
)
WINDOW_DISPOSITIONS = (
    "VIABLE",
    "PATHOLOGICALLY_FRAGMENTED",
    "STRUCTURALLY_INSUFFICIENT",
    "EPISTEMICALLY_INDETERMINATE",
)
PATH_DISPOSITIONS = (
    "VIABLE",
    "VIABLE_AFTER_24H_FALLBACK",
    "VIABLE_AFTER_1H_FALLBACK",
    "PATHOLOGICALLY_FRAGMENTED",
    "STRUCTURALLY_INSUFFICIENT",
    "EPISTEMICALLY_INDETERMINATE",
)
FINAL_DISPOSITIONS = (
    "LRS4_SOURCE_HISTORY_INELIGIBLE",
    "LRS4_REGIME_INELIGIBLE",
    "LRS4_ELIGIBLE",
)


@dataclass(frozen=True)
class Gate2Evidence:
    """Completed inherited E_W = (R_W, A_W, H_W)."""

    window: Window
    reasons: frozenset[Gate2Reason]
    action: ResolutionAction
    disposition: WindowDisposition

    def __post_init__(self) -> None:
        _require_member("window", self.window, WINDOWS)
        if type(self.reasons) is not frozenset:
            raise TypeError("reasons must be a frozenset")
        for reason in self.reasons:
            _require_member("reason", reason, REASONS)
        _require_member("action", self.action, ACTIONS)
        _require_member("disposition", self.disposition, WINDOW_DISPOSITIONS)
        structural = {
            "SEVERE_REGIME_IMBALANCE",
            "EXCESSIVE_REGIME_INELIGIBILITY",
            "EXCESSIVE_INELIGIBILITY_CONCENTRATION",
            "INSUFFICIENT_STATE_EPISODE_SUPPORT",
        }
        epistemic = (
            "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING"
        )
        turnover = "EXCESSIVE_EPISODE_TURNOVER"
        persistence = "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE"
        conflict = "CONFLICTING_DIRECTIONAL_FAILURES"

        both = turnover in self.reasons and persistence in self.reasons
        if (conflict in self.reasons) != both:
            raise ValueError(
                "derived directional conflict must occur exactly when "
                "both directional reasons are present"
            )

        if self.reasons & structural or conflict in self.reasons:
            expected_disposition = "STRUCTURALLY_INSUFFICIENT"
        elif epistemic in self.reasons:
            expected_disposition = "EPISTEMICALLY_INDETERMINATE"
        elif persistence in self.reasons:
            expected_disposition = "STRUCTURALLY_INSUFFICIENT"
        elif turnover in self.reasons:
            expected_disposition = "PATHOLOGICALLY_FRAGMENTED"
        else:
            expected_disposition = "VIABLE"

        if self.disposition != expected_disposition:
            raise ValueError(
                "H_W contradicts the complete Gate-2 reason set"
            )

        if not self.reasons:
            expected_action = "PROCEED_TO_STAGE_2"
        elif self.reasons & structural or epistemic in self.reasons or both:
            expected_action = "TERMINATE_INSTRUMENT_V1"
        elif self.window != "4h":
            expected_action = "TERMINATE_INSTRUMENT_V1"
        elif turnover in self.reasons:
            expected_action = "EVALUATE_24H_FALLBACK"
        elif persistence in self.reasons:
            expected_action = "EVALUATE_1H_FALLBACK"
        else:
            raise ValueError("unresolved Gate-2 reason configuration")

        if self.action != expected_action:
            raise ValueError(
                "A_W contradicts the frozen primary/fallback resolution rules"
            )


@dataclass(frozen=True)
class WindowD0Terminal:
    tag: Literal["D0_TERMINAL"]
    window: Window
    reason: Literal["NO_TARGET_OBSERVATION_POPULATION"]
    provenance: D0Provenance

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("D0_TERMINAL",))
        _require_member("window", self.window, WINDOWS)
        _require_member(
            "reason", self.reason, ("NO_TARGET_OBSERVATION_POPULATION",)
        )
        _require_member("provenance", self.provenance, ("C1", "C2"))


@dataclass(frozen=True)
class WindowGate2Completed:
    tag: Literal["GATE2_COMPLETED"]
    evidence: Gate2Evidence

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("GATE2_COMPLETED",))
        if type(self.evidence) is not Gate2Evidence:
            raise TypeError("evidence must be Gate2Evidence")


@dataclass(frozen=True)
class WindowIntegrityFailure:
    tag: Literal["INTEGRITY_FAILURE"]
    window: Window
    invariant: str
    provenance: str

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("INTEGRITY_FAILURE",))
        _require_member("window", self.window, WINDOWS)
        _require_nonempty("invariant", self.invariant)
        _require_nonempty("provenance", self.provenance)


WindowEvaluationResult: TypeAlias = Union[
    WindowD0Terminal,
    WindowGate2Completed,
    WindowIntegrityFailure,
]


@dataclass(frozen=True)
class InstrumentPathProvenance:
    """Ordered entered-window history, without routing calculations."""

    entered: tuple[WindowEvaluationResult, ...]
    h_path: PathDisposition | None = None

    def __post_init__(self) -> None:
        if type(self.entered) is not tuple or not 1 <= len(self.entered) <= 2:
            raise ValueError("entered must contain one or two evaluations")
        for entry in self.entered:
            if type(entry) not in (
                WindowD0Terminal,
                WindowGate2Completed,
                WindowIntegrityFailure,
            ):
                raise TypeError("invalid entered-window result")
        if self.h_path is not None:
            _require_member("h_path", self.h_path, PATH_DISPOSITIONS)

        def window_of(entry):
            if type(entry) is WindowGate2Completed:
                return entry.evidence.window
            return entry.window

        windows = tuple(window_of(entry) for entry in self.entered)
        if windows not in (("4h",), ("4h", "24h"), ("4h", "1h")):
            raise ValueError("instrument path has an unauthorized window shape")

        if len(self.entered) == 2:
            primary, fallback = self.entered
            if type(primary) is not WindowGate2Completed:
                raise ValueError("fallback requires completed primary Gate 2")
            required_action = (
                "EVALUATE_24H_FALLBACK" if windows[1] == "24h"
                else "EVALUATE_1H_FALLBACK"
            )
            if primary.evidence.action != required_action:
                raise ValueError("fallback lacks primary authorization")
            if type(fallback) is WindowGate2Completed and (
                fallback.evidence.action not in (
                    "PROCEED_TO_STAGE_2",
                    "TERMINATE_INSTRUMENT_V1",
                )
            ):
                raise ValueError("fallback requested a second fallback")
        elif type(self.entered[0]) is WindowGate2Completed:
            if self.entered[0].evidence.action in (
                "EVALUATE_24H_FALLBACK",
                "EVALUATE_1H_FALLBACK",
            ):
                raise ValueError("authorized fallback evaluation is missing")


@dataclass(frozen=True)
class PathViable:
    tag: Literal["VIABLE"]
    realized_window: Window
    provenance: InstrumentPathProvenance

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("VIABLE",))
        _require_member("realized_window", self.realized_window, WINDOWS)
        if type(self.provenance) is not InstrumentPathProvenance:
            raise TypeError("invalid path provenance")
        last = self.provenance.entered[-1]
        if type(last) is not WindowGate2Completed:
            raise ValueError("viable path requires completed final Gate 2")
        if last.evidence.action != "PROCEED_TO_STAGE_2":
            raise ValueError("viable path requires Gate-2 proceed action")
        if self.realized_window != last.evidence.window:
            raise ValueError("realized window differs from final entered window")
        expected_h = {
            "4h": "VIABLE",
            "24h": "VIABLE_AFTER_24H_FALLBACK",
            "1h": "VIABLE_AFTER_1H_FALLBACK",
        }[self.realized_window]
        if self.provenance.h_path != expected_h:
            raise ValueError("viable path has incorrect H_path")


@dataclass(frozen=True)
class PathGate2Terminal:
    tag: Literal["GATE2_TERMINAL"]
    provenance: InstrumentPathProvenance

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("GATE2_TERMINAL",))
        if type(self.provenance) is not InstrumentPathProvenance:
            raise TypeError("invalid path provenance")
        last = self.provenance.entered[-1]
        if type(last) is not WindowGate2Completed:
            raise ValueError("Gate-2 terminal requires completed final Gate 2")
        if last.evidence.action != "TERMINATE_INSTRUMENT_V1":
            raise ValueError("Gate-2 terminal requires termination action")
        if self.provenance.h_path != last.evidence.disposition:
            raise ValueError("terminal H_path contradicts final Gate-2 diagnosis")


@dataclass(frozen=True)
class PathD0Terminal:
    tag: Literal["D0_TERMINAL"]
    provenance: InstrumentPathProvenance

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("D0_TERMINAL",))
        if type(self.provenance) is not InstrumentPathProvenance:
            raise TypeError("invalid path provenance")
        if type(self.provenance.entered[-1]) is not WindowD0Terminal:
            raise ValueError("D0 terminal requires final D0 result")
        if self.provenance.h_path is not None:
            raise ValueError("D0 terminal cannot assert Gate-2 H_path")


@dataclass(frozen=True)
class PathIntegrityFailure:
    tag: Literal["INTEGRITY_FAILURE"]
    invariant: str
    provenance: str

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("INTEGRITY_FAILURE",))
        _require_nonempty("invariant", self.invariant)
        _require_nonempty("provenance", self.provenance)


InstrumentPathResult: TypeAlias = Union[
    PathViable,
    PathGate2Terminal,
    PathD0Terminal,
    PathIntegrityFailure,
]


@dataclass(frozen=True)
class FinalObservationResolved:
    tag: Literal["RESOLVED"]
    disposition: FinalObservationDisposition

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("RESOLVED",))
        _require_member("disposition", self.disposition, FINAL_DISPOSITIONS)

    @property
    def final_eligible(self) -> bool:
        return self.disposition == "LRS4_ELIGIBLE"


@dataclass(frozen=True)
class FinalObservationIntegrityFailure:
    tag: Literal["INTEGRITY_FAILURE"]
    invariant: str
    provenance: str

    def __post_init__(self) -> None:
        _require_member("tag", self.tag, ("INTEGRITY_FAILURE",))
        _require_nonempty("invariant", self.invariant)
        _require_nonempty("provenance", self.provenance)


FinalObservationResult: TypeAlias = Union[
    FinalObservationResolved,
    FinalObservationIntegrityFailure,
]
