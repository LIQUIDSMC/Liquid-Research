"""Structured Gate-2 integrity exception with exact provenance."""


class Gate2IntegrityError(ValueError):
    """Validation failure with explicit invariant identity and provenance."""

    def __init__(self, invariant: str, provenance: str):
        super().__init__(provenance)
        self.invariant = invariant
        self.provenance = provenance
