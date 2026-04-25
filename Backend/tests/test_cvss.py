"""
Tests for CVSS v3.1 calculator (Task 9).
Covers: scoring math against known vectors, edge cases, validation,
vector string round-trip, and the /cvss_score/ API endpoint.
"""
import pytest
from core.cvss import CVSSMetrics, CVSSv3Calculator, CVSSResult, calculate_cvss


# ---------------------------------------------------------------------------
# Known-vector regression tests (values from the CVSS v3.1 spec examples)
# ---------------------------------------------------------------------------

class TestCVSSKnownVectors:
    """
    Reference scores taken from the FIRST CVSS v3.1 calculator
    https://www.first.org/cvss/calculator/3.1
    """

    def _calc(self, av, ac, pr, ui, s, c, i, a):
        return calculate_cvss(av, ac, pr, ui, s, c, i, a)

    def test_critical_rce_score(self):
        """AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H → 9.8 Critical"""
        r = self._calc('N', 'L', 'N', 'N', 'U', 'H', 'H', 'H')
        assert r.base_score == 9.8
        assert r.severity == 'Critical'

    def test_high_authenticated_rce(self):
        """AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H → 8.8 High"""
        r = self._calc('N', 'L', 'L', 'N', 'U', 'H', 'H', 'H')
        assert r.base_score == 8.8
        assert r.severity == 'High'

    def test_medium_xss(self):
        """AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N → 6.1 Medium"""
        r = self._calc('N', 'L', 'N', 'R', 'C', 'L', 'L', 'N')
        assert r.base_score == 6.1
        assert r.severity == 'Medium'

    def test_low_info_disclosure(self):
        """AV:L/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N → 2.9 Low"""
        r = self._calc('L', 'H', 'N', 'N', 'U', 'L', 'N', 'N')
        assert r.base_score == 2.9
        assert r.severity == 'Low'

    def test_zero_impact_score(self):
        """All CIA=N → 0.0 None"""
        r = self._calc('N', 'L', 'N', 'N', 'U', 'N', 'N', 'N')
        assert r.base_score == 0.0
        assert r.severity == 'None'

    def test_scope_changed_high(self):
        """AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H → 10.0 Critical"""
        r = self._calc('N', 'L', 'N', 'N', 'C', 'H', 'H', 'H')
        assert r.base_score == 10.0
        assert r.severity == 'Critical'

    def test_physical_access_low(self):
        """AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N → 1.0 Low"""
        r = self._calc('P', 'H', 'H', 'R', 'U', 'L', 'N', 'N')
        assert r.base_score == 1.0
        assert r.severity == 'Low'

    def test_adjacent_medium(self):
        """AV:A/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L → 6.3 Medium"""
        r = self._calc('A', 'L', 'N', 'N', 'U', 'L', 'L', 'L')
        assert r.base_score == 6.3
        assert r.severity == 'Medium'


# ---------------------------------------------------------------------------
# Severity boundary tests
# ---------------------------------------------------------------------------

class TestSeverityBoundaries:
    def test_score_0_is_none(self):
        assert CVSSv3Calculator._severity_label(0.0) == 'None'

    def test_score_0_1_is_low(self):
        assert CVSSv3Calculator._severity_label(0.1) == 'Low'

    def test_score_3_9_is_low(self):
        assert CVSSv3Calculator._severity_label(3.9) == 'Low'

    def test_score_4_0_is_medium(self):
        assert CVSSv3Calculator._severity_label(4.0) == 'Medium'

    def test_score_6_9_is_medium(self):
        assert CVSSv3Calculator._severity_label(6.9) == 'Medium'

    def test_score_7_0_is_high(self):
        assert CVSSv3Calculator._severity_label(7.0) == 'High'

    def test_score_8_9_is_high(self):
        assert CVSSv3Calculator._severity_label(8.9) == 'High'

    def test_score_9_0_is_critical(self):
        assert CVSSv3Calculator._severity_label(9.0) == 'Critical'

    def test_score_10_is_critical(self):
        assert CVSSv3Calculator._severity_label(10.0) == 'Critical'


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestCVSSValidation:
    def test_invalid_attack_vector_raises(self):
        with pytest.raises(ValueError, match="Invalid AV"):
            CVSSv3Calculator(CVSSMetrics('X', 'L', 'N', 'N', 'U', 'H', 'H', 'H'))

    def test_invalid_cia_raises(self):
        with pytest.raises(ValueError):
            CVSSv3Calculator(CVSSMetrics('N', 'L', 'N', 'N', 'U', 'X', 'H', 'H'))

    def test_lowercase_values_raise(self):
        """Values must be uppercase abbreviations."""
        with pytest.raises(ValueError):
            CVSSv3Calculator(CVSSMetrics('n', 'l', 'n', 'n', 'u', 'h', 'h', 'h'))

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            CVSSv3Calculator(CVSSMetrics('', 'L', 'N', 'N', 'U', 'H', 'H', 'H'))


# ---------------------------------------------------------------------------
# Vector string round-trip
# ---------------------------------------------------------------------------

class TestVectorString:
    def test_to_vector_string(self):
        m = CVSSMetrics('N', 'L', 'N', 'N', 'U', 'H', 'H', 'H')
        assert m.to_vector_string() == 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'

    def test_from_vector_string_round_trip(self):
        original = CVSSMetrics('N', 'L', 'N', 'N', 'U', 'H', 'H', 'H')
        parsed = CVSSMetrics.from_vector_string(original.to_vector_string())
        assert parsed == original

    def test_result_includes_vector_string(self):
        r = calculate_cvss('N', 'L', 'N', 'N', 'U', 'H', 'H', 'H')
        assert r.vector_string.startswith('CVSS:3.1/')

    def test_roundup_spec_compliance(self):
        """CVSS roundup: 4.02 → 4.1, not 4.0"""
        assert CVSSv3Calculator._roundup(4.02) == 4.1
        assert CVSSv3Calculator._roundup(4.00) == 4.0
        assert CVSSv3Calculator._roundup(9.95) == 10.0


# ---------------------------------------------------------------------------
# API endpoint: POST /api/reports/{id}/cvss_score/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCVSSEndpoint:
    def _url(self, report_id):
        return f'/api/reports/{report_id}/cvss_score/'

    def _payload(self, **overrides):
        base = {
            'attack_vector': 'N',
            'attack_complexity': 'L',
            'privileges_required': 'N',
            'user_interaction': 'N',
            'scope': 'U',
            'confidentiality': 'H',
            'integrity': 'H',
            'availability': 'H',
        }
        base.update(overrides)
        return base

    def test_returns_score_and_severity(self, api_client, own_report, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self._url(own_report.id), self._payload(), format='json')
        assert resp.status_code == 200
        assert resp.data['base_score'] == 9.8
        assert resp.data['severity'] == 'Critical'
        assert 'vector_string' in resp.data

    def test_unauthenticated_returns_401(self, api_client, own_report):
        resp = api_client.post(self._url(own_report.id), self._payload(), format='json')
        assert resp.status_code == 401

    def test_invalid_metric_returns_400(self, api_client, own_report, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            self._url(own_report.id),
            self._payload(attack_vector='INVALID'),
            format='json'
        )
        assert resp.status_code == 400

    def test_missing_field_returns_400(self, api_client, own_report, verified_user):
        api_client.force_authenticate(user=verified_user)
        payload = self._payload()
        del payload['attack_vector']
        resp = api_client.post(self._url(own_report.id), payload, format='json')
        assert resp.status_code == 400

    def test_save_requires_triager_or_admin(self, api_client, own_report, verified_user):
        """A plain researcher must not be able to persist CVSS scores."""
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            self._url(own_report.id),
            {**self._payload(), 'save': True},
            format='json'
        )
        assert resp.status_code == 403

    def test_triager_can_save_cvss_score(self, api_client, own_report, triager_user):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(
            self._url(own_report.id),
            {**self._payload(), 'save': True},
            format='json'
        )
        assert resp.status_code == 200
        own_report.refresh_from_db()
        assert own_report.cvss_score == 9.8
        assert own_report.cvss_severity == 'Critical'
        assert own_report.cvss_vector.startswith('CVSS:3.1/')

    def test_score_without_save_does_not_persist(self, api_client, own_report, verified_user):
        api_client.force_authenticate(user=verified_user)
        api_client.post(self._url(own_report.id), self._payload(), format='json')
        own_report.refresh_from_db()
        assert own_report.cvss_score is None  # not saved
