"""
CVSS v3.1 Base Score Calculator.

Implements the full CVSS v3.1 specification:
https://www.first.org/cvss/v3.1/specification-document

Usage:
    from core.cvss import CVSSv3Calculator, CVSSMetrics

    metrics = CVSSMetrics(
        attack_vector='N',          # Network
        attack_complexity='L',      # Low
        privileges_required='N',    # None
        user_interaction='N',       # None
        scope='U',                  # Unchanged
        confidentiality='H',        # High
        integrity='H',              # High
        availability='H',           # High
    )
    calc = CVSSv3Calculator(metrics)
    result = calc.calculate()
    # result.base_score  => 9.8  (Critical)
    # result.severity    => "Critical"
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import math


# ---------------------------------------------------------------------------
# Metric value tables (CVSS v3.1 spec, Section 7.1)
# ---------------------------------------------------------------------------

ATTACK_VECTOR = {
    'N': 0.85,   # Network
    'A': 0.62,   # Adjacent
    'L': 0.55,   # Local
    'P': 0.20,   # Physical
}

ATTACK_COMPLEXITY = {
    'L': 0.77,   # Low
    'H': 0.44,   # High
}

PRIVILEGES_REQUIRED_UNCHANGED = {
    'N': 0.85,   # None
    'L': 0.62,   # Low
    'H': 0.27,   # High
}

PRIVILEGES_REQUIRED_CHANGED = {
    'N': 0.85,   # None
    'L': 0.68,   # Low  ← differs when Scope is Changed
    'H': 0.50,   # High ← differs when Scope is Changed
}

USER_INTERACTION = {
    'N': 0.85,   # None
    'R': 0.62,   # Required
}

SCOPE = {
    'U': False,  # Unchanged
    'C': True,   # Changed
}

CIA_IMPACT = {
    'N': 0.00,   # None
    'L': 0.22,   # Low
    'H': 0.56,   # High
}

SEVERITY_LABELS = [
    (0.0,  0.0,  'None'),
    (0.1,  3.9,  'Low'),
    (4.0,  6.9,  'Medium'),
    (7.0,  8.9,  'High'),
    (9.0,  10.0, 'Critical'),
]


# ---------------------------------------------------------------------------
# Input / Output types
# ---------------------------------------------------------------------------

@dataclass
class CVSSMetrics:
    """
    CVSS v3.1 Base Metric Group.

    All values are the single-letter abbreviations used in CVSS vector strings.
    """
    attack_vector: Literal['N', 'A', 'L', 'P']
    attack_complexity: Literal['L', 'H']
    privileges_required: Literal['N', 'L', 'H']
    user_interaction: Literal['N', 'R']
    scope: Literal['U', 'C']
    confidentiality: Literal['N', 'L', 'H']
    integrity: Literal['N', 'L', 'H']
    availability: Literal['N', 'L', 'H']

    def to_vector_string(self) -> str:
        return (
            f"CVSS:3.1/AV:{self.attack_vector}/AC:{self.attack_complexity}"
            f"/PR:{self.privileges_required}/UI:{self.user_interaction}"
            f"/S:{self.scope}/C:{self.confidentiality}"
            f"/I:{self.integrity}/A:{self.availability}"
        )

    @classmethod
    def from_vector_string(cls, vector: str) -> 'CVSSMetrics':
        """Parse a CVSS v3.1 vector string, e.g. CVSS:3.1/AV:N/AC:L/..."""
        parts = {}
        for segment in vector.split('/'):
            if ':' in segment:
                key, val = segment.split(':', 1)
                parts[key] = val
        return cls(
            attack_vector=parts['AV'],
            attack_complexity=parts['AC'],
            privileges_required=parts['PR'],
            user_interaction=parts['UI'],
            scope=parts['S'],
            confidentiality=parts['C'],
            integrity=parts['I'],
            availability=parts['A'],
        )


@dataclass
class CVSSResult:
    base_score: float
    severity: str
    iss: float          # Impact Sub-Score
    ess: float          # Exploitability Sub-Score
    vector_string: str


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class CVSSv3Calculator:
    """
    Stateless CVSS v3.1 Base Score calculator.

    Instantiate with a CVSSMetrics object and call .calculate().
    """

    VALID_ATTACK_VECTORS = set(ATTACK_VECTOR)
    VALID_ATTACK_COMPLEXITY = set(ATTACK_COMPLEXITY)
    VALID_PRIVILEGES_REQUIRED = set(PRIVILEGES_REQUIRED_UNCHANGED)
    VALID_USER_INTERACTION = set(USER_INTERACTION)
    VALID_SCOPE = set(SCOPE)
    VALID_CIA = set(CIA_IMPACT)

    def __init__(self, metrics: CVSSMetrics):
        self.metrics = metrics
        self._validate()

    def _validate(self):
        m = self.metrics
        errors = []
        if m.attack_vector not in self.VALID_ATTACK_VECTORS:
            errors.append(f"Invalid AV: {m.attack_vector!r}. Must be one of {sorted(self.VALID_ATTACK_VECTORS)}")
        if m.attack_complexity not in self.VALID_ATTACK_COMPLEXITY:
            errors.append(f"Invalid AC: {m.attack_complexity!r}. Must be one of {sorted(self.VALID_ATTACK_COMPLEXITY)}")
        if m.privileges_required not in self.VALID_PRIVILEGES_REQUIRED:
            errors.append(f"Invalid PR: {m.privileges_required!r}. Must be one of {sorted(self.VALID_PRIVILEGES_REQUIRED)}")
        if m.user_interaction not in self.VALID_USER_INTERACTION:
            errors.append(f"Invalid UI: {m.user_interaction!r}. Must be one of {sorted(self.VALID_USER_INTERACTION)}")
        if m.scope not in self.VALID_SCOPE:
            errors.append(f"Invalid S: {m.scope!r}. Must be one of {sorted(self.VALID_SCOPE)}")
        for label, val in [('C', m.confidentiality), ('I', m.integrity), ('A', m.availability)]:
            if val not in self.VALID_CIA:
                errors.append(f"Invalid {label}: {val!r}. Must be one of {sorted(self.VALID_CIA)}")
        if errors:
            raise ValueError("Invalid CVSS metrics:\n" + "\n".join(f"  - {e}" for e in errors))

    def calculate(self) -> CVSSResult:
        m = self.metrics
        scope_changed = SCOPE[m.scope]

        # Exploitability Sub-Score
        pr_table = PRIVILEGES_REQUIRED_CHANGED if scope_changed else PRIVILEGES_REQUIRED_UNCHANGED
        ess = (
            8.22
            * ATTACK_VECTOR[m.attack_vector]
            * ATTACK_COMPLEXITY[m.attack_complexity]
            * pr_table[m.privileges_required]
            * USER_INTERACTION[m.user_interaction]
        )

        # Impact Sub-Score
        isc_base = 1 - (
            (1 - CIA_IMPACT[m.confidentiality])
            * (1 - CIA_IMPACT[m.integrity])
            * (1 - CIA_IMPACT[m.availability])
        )

        if not scope_changed:
            iss = 6.42 * isc_base
        else:
            iss = 7.52 * (isc_base - 0.029) - 3.25 * ((isc_base - 0.02) ** 15)

        # Base Score
        if iss <= 0:
            base_score = 0.0
        else:
            if not scope_changed:
                raw = min(iss + ess, 10)
            else:
                raw = min(1.08 * (iss + ess), 10)
            # Round up to nearest 0.1 (CVSS spec uses "roundup" not "round")
            base_score = self._roundup(raw)

        severity = self._severity_label(base_score)

        return CVSSResult(
            base_score=base_score,
            severity=severity,
            iss=round(iss, 4),
            ess=round(ess, 4),
            vector_string=m.to_vector_string(),
        )

    @staticmethod
    def _roundup(value: float) -> float:
        """
        CVSS spec §7.4: 'Roundup' returns the smallest number,
        specified to 1 decimal place, that is equal to or higher than its input.
        """
        int_val = math.ceil(value * 10)
        return int_val / 10

    @staticmethod
    def _severity_label(score: float) -> str:
        for lo, hi, label in SEVERITY_LABELS:
            if lo <= score <= hi:
                return label
        return 'None'


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def calculate_cvss(
    attack_vector: str,
    attack_complexity: str,
    privileges_required: str,
    user_interaction: str,
    scope: str,
    confidentiality: str,
    integrity: str,
    availability: str,
) -> CVSSResult:
    """Thin wrapper for direct calls without building a CVSSMetrics object."""
    metrics = CVSSMetrics(
        attack_vector=attack_vector,
        attack_complexity=attack_complexity,
        privileges_required=privileges_required,
        user_interaction=user_interaction,
        scope=scope,
        confidentiality=confidentiality,
        integrity=integrity,
        availability=availability,
    )
    return CVSSv3Calculator(metrics).calculate()
