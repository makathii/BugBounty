"""
Tests for duplicate submission detection and handling.
"""
import pytest
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from reports.models import BugReport
from programs.models import Program


@pytest.fixture
def client():
    """Returns an unauthenticated client"""
    return APIClient()


@pytest.fixture
def triager_user(db):
    """Create a user with triager role"""
    user = User.objects.create_user(
        username='triager',
        password='testpass123',
        email='triager@test.com'
    )
    triager_group, _ = Group.objects.get_or_create(name='Triager')
    user.groups.add(triager_group)
    return user


@pytest.fixture
def regular_user(db):
    """Create a verified regular user"""
    user = User.objects.create_user(
        username='researcher',
        password='testpass123',
        email='researcher@test.com'
    )
    # Create profile and verify email
    from users.models import Profile
    profile = Profile.objects.get_or_create(user=user)[0]
    profile.email_verified = True
    profile.save()
    return user


@pytest.fixture
def company_user(db):
    """Create a company user who owns programs"""
    return User.objects.create_user(
        username='testcompany',
        password='testpass123',
        email='company@test.com'
    )


@pytest.fixture
def program(db, company_user):
    """Create a test program"""
    return Program.objects.create(
        name='Test Program',
        description='Test program for duplicate detection',
        company=company_user,
        status='active'
    )


@pytest.fixture
def existing_report(db, regular_user, program):
    """Create an existing bug report for duplicate testing"""
    return BugReport.objects.create(
        title='SQL Injection on Login Page',
        description='Found a SQL injection vulnerability in the login form',
        reporter=regular_user,
        program=program,
        severity='high',
        affected_url='https://example.com/login',
        vulnerability_type='SQL Injection',
        steps_to_reproduce='1. Go to login\n2. Enter \' OR 1=1--\n3. Submit'
    )


@pytest.mark.django_db
class TestDuplicateDetection:
    """Tests for the find_potential_duplicates model method"""

    def test_find_duplicates_by_similar_title(self, existing_report, program):
        """Test that similar titles are detected as potential duplicates"""
        # Create a new report with very similar title and description
        new_report = BugReport(
            title='SQL Injection on Login Form',  # Very similar to existing
            description='SQL injection vulnerability in login form found',  # Similar keywords
            affected_url='https://other.com/page',
            program=program
        )

        duplicates = new_report.find_potential_duplicates(threshold=0.6)

        # Should find the existing report
        assert len(duplicates) > 0
        found_ids = [dup[0].id for dup in duplicates]
        assert existing_report.id in found_ids

    def test_find_duplicates_by_exact_url(self, existing_report, program):
        """Test that exact URL matches are detected"""
        new_report = BugReport(
            title='Completely Different Title',
            description='Totally different description about XSS',
            affected_url='https://example.com/login',  # Same URL
            program=program
        )

        duplicates = new_report.find_potential_duplicates(threshold=0.5)

        # Should find the existing report due to URL match (boosted score)
        assert len(duplicates) > 0
        found_ids = [dup[0].id for dup in duplicates]
        assert existing_report.id in found_ids

    def test_no_duplicates_for_different_content(self, existing_report, program):
        """Test that completely different reports are not flagged"""
        new_report = BugReport(
            title='XSS on Profile Page',
            description='Cross-site scripting vulnerability in user profile',
            affected_url='https://example.com/profile',
            program=program
        )

        duplicates = new_report.find_potential_duplicates(threshold=0.8)

        # Should not find the existing report (too different)
        found_ids = [dup[0].id for dup in duplicates]
        assert existing_report.id not in found_ids

    def test_excludes_already_duplicate_reports(self, existing_report, program, triager_user):
        """Test that reports already marked as duplicate are excluded"""
        # Create an original report
        original = BugReport.objects.create(
            title='Original Report',
            description='Original description',
            reporter=existing_report.reporter,
            program=program,
            affected_url='https://example.com/original'
        )

        # Mark existing as duplicate
        existing_report.status = 'duplicate'
        existing_report.duplicate_of = original
        existing_report.save()

        # Create new report similar to the duplicate
        new_report = BugReport(
            title='SQL Injection on Login Page',  # Same as existing
            description='Found a SQL injection vulnerability',
            affected_url='https://example.com/login',
            program=program
        )

        duplicates = new_report.find_potential_duplicates(threshold=0.7)

        # Should NOT include the report marked as duplicate
        found_ids = [dup[0].id for dup in duplicates]
        assert existing_report.id not in found_ids


@pytest.mark.django_db
class TestDuplicateCheckEndpoint:
    """Tests for the POST /check_duplicates/ endpoint"""

    def test_check_duplicates_returns_matches(self, client, regular_user, existing_report):
        """Test the check_duplicates endpoint returns potential matches"""
        client.force_authenticate(user=regular_user)

        response = client.post('/api/reports/reports/check_duplicates/', {
            'title': 'SQL Injection on Login Page',  # Very similar
            'description': 'SQL injection vulnerability found',
            'affected_url': 'https://example.com/login',
            'program': existing_report.program.id
        }, format='json')

        assert response.status_code == 200
        assert response.data['has_duplicates'] is True
        assert len(response.data['potential_duplicates']) > 0
        # Check the duplicate has expected fields
        dup = response.data['potential_duplicates'][0]
        assert 'id' in dup
        assert 'title' in dup
        assert 'similarity' in dup
        assert 'reporter' in dup

    def test_check_duplicates_no_matches(self, client, regular_user, existing_report):
        """Test the check_duplicates endpoint when no duplicates found"""
        client.force_authenticate(user=regular_user)

        response = client.post('/api/reports/reports/check_duplicates/', {
            'title': 'XSS on Search Page',
            'description': 'Cross site scripting in search functionality',
            'affected_url': 'https://example.com/search',
            'program': existing_report.program.id
        }, format='json')

        assert response.status_code == 200
        assert response.data['has_duplicates'] is False
        assert len(response.data['potential_duplicates']) == 0

    def test_check_duplicates_requires_authentication(self, client):
        """Test that unauthenticated users cannot check duplicates"""
        response = client.post('/api/reports/reports/check_duplicates/', {
            'title': 'Test Title',
            'description': 'Test description'
        }, format='json')

        assert response.status_code == 401  # Unauthorized

    def test_check_duplicates_requires_title_and_description(self, client, regular_user):
        """Test validation that title and description are required"""
        client.force_authenticate(user=regular_user)

        response = client.post('/api/reports/reports/check_duplicates/', {
            'title': '',
            'description': ''
        }, format='json')

        assert response.status_code == 400
        assert 'error' in response.data


@pytest.mark.django_db
class TestSerializerDuplicateValidation:
    """Tests that the serializer blocks submission of obvious duplicates"""

    def test_serializer_blocks_high_similarity_duplicates(self, regular_user, existing_report, program):
        """Test that serializer validation catches very similar reports"""
        from reports.serializers import BugReportSerializer

        data = {
            'title': 'SQL Injection on Login Page',  # Nearly identical
            'description': 'Found a SQL injection vulnerability in the login form',
            'severity': 'high',
            'affected_url': 'https://example.com/login',
            'program': program.id
        }

        serializer = BugReportSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid is False
        assert 'potential_duplicates' in serializer.errors
        assert 'message' in serializer.errors

    def test_serializer_allows_different_reports(self, regular_user, existing_report, program):
        """Test that different reports pass validation"""
        from reports.serializers import BugReportSerializer

        data = {
            'title': 'XSS Vulnerability in Comments',
            'description': 'Cross-site scripting vulnerability in the comment system',
            'severity': 'medium',
            'affected_url': 'https://example.com/comments',
            'program': program.id
        }

        serializer = BugReportSerializer(data=data)
        is_valid = serializer.is_valid()

        assert is_valid is True


@pytest.mark.django_db
class TestMarkAsDuplicateEndpoint:
    """Tests for the POST /{id}/mark_as_duplicate/ endpoint"""

    def test_triager_can_mark_duplicate(self, client, triager_user, existing_report, program):
        """Test that triagers can mark reports as duplicate"""
        # Create an original report
        original = BugReport.objects.create(
            title='Original SQL Injection',
            description='First report of SQL injection',
            reporter=existing_report.reporter,
            program=program,
            affected_url='https://example.com/login'
        )

        client.force_authenticate(user=triager_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_of': original.id,
                'duplicate_reason': 'Same vulnerability, reported later'
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['status'] == 'duplicate'
        assert response.data['duplicate_of'] == original.id

        # Verify database was updated
        existing_report.refresh_from_db()
        assert existing_report.status == 'duplicate'
        assert existing_report.duplicate_of == original

    def test_regular_user_cannot_mark_duplicate(self, client, regular_user, existing_report, program):
        """Test that regular users cannot mark duplicates"""
        original = BugReport.objects.create(
            title='Original Report',
            description='Original description',
            reporter=regular_user,
            program=program
        )

        client.force_authenticate(user=regular_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_of': original.id,
                'duplicate_reason': 'Test'
            },
            format='json'
        )

        assert response.status_code == 403  # Forbidden

    def test_cannot_mark_self_as_duplicate(self, client, triager_user, existing_report):
        """Test that a report cannot be marked as duplicate of itself"""
        client.force_authenticate(user=triager_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_of': existing_report.id,  # Same ID
                'duplicate_reason': 'Self reference'
            },
            format='json'
        )

        assert response.status_code == 400
        assert 'error' in response.data

    def test_cannot_mark_as_duplicate_of_duplicate(self, client, triager_user, existing_report, program):
        """Test that you cannot mark as duplicate of a report that is itself a duplicate"""
        # Create a chain: original -> duplicate_of_original
        original = BugReport.objects.create(
            title='Original',
            description='Original report',
            reporter=existing_report.reporter,
            program=program
        )

        middle_report = BugReport.objects.create(
            title='Middle Report',
            description='Already a duplicate',
            reporter=existing_report.reporter,
            program=program,
            status='duplicate',
            duplicate_of=original
        )

        client.force_authenticate(user=triager_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_of': middle_report.id,  # This is already a duplicate
                'duplicate_reason': 'Test'
            },
            format='json'
        )

        assert response.status_code == 400
        assert 'error' in response.data

    def test_requires_duplicate_of_id(self, client, triager_user, existing_report):
        """Test that duplicate_of field is required"""
        client.force_authenticate(user=triager_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_reason': 'Missing the ID'
            },
            format='json'
        )

        assert response.status_code == 400
        assert 'error' in response.data

    def test_invalid_duplicate_of_id(self, client, triager_user, existing_report):
        """Test that invalid report ID returns error"""
        client.force_authenticate(user=triager_user)

        response = client.post(
            f'/api/reports/reports/{existing_report.id}/mark_as_duplicate/',
            {
                'duplicate_of': 999999,  # Non-existent
                'duplicate_reason': 'Test'
            },
            format='json'
        )

        assert response.status_code == 404
