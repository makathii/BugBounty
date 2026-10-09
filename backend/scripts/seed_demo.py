"""
Demo data seeder for trailer recording.
Run: docker exec -i bugbounty-backend python manage.py shell < scripts/seed_demo.py
Idempotent — safe to run multiple times.
All demo accounts use the password: Demo1234!
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User, Group
from django.utils import timezone

from programs.models import Company, Program
from reports.models import BugReport
from users.models import Profile

PASSWORD = "Demo1234!"

researcher_g, _ = Group.objects.get_or_create(name="Researcher")
owner_g, _ = Group.objects.get_or_create(name="ProgramOwner")
triager_g, _ = Group.objects.get_or_create(name="Triager")
admin_g, _ = Group.objects.get_or_create(name="Admin")


def make_user(username, email, first, last, groups, role=Profile.ROLE_USER, superuser=False):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "first_name": first, "last_name": last},
    )
    if created:
        user.set_password(PASSWORD)
    user.is_active = True
    if superuser:
        user.is_superuser = True
        user.is_staff = True
    user.save()
    user.groups.set(groups)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.email_verified = True
    profile.role = role
    profile.save()
    return user


admin = make_user("admin", "admin@bugbounty.local", "Ada", "Admin", [admin_g], Profile.ROLE_ADMIN, superuser=True)
triager = make_user("triager", "triage@bugbounty.local", "Tara", "Triage", [triager_g])
acme = make_user("acme", "security@acme.example", "Alice", "Acme", [owner_g], Profile.ROLE_PROGRAM_OWNER)
techflow = make_user("techflow", "security@techflow.example", "Tom", "Flow", [owner_g], Profile.ROLE_PROGRAM_OWNER)
parsa = make_user("parsa", "parsa@hunter.example", "Parsa", "F.", [researcher_g])
nova = make_user("nova", "nova@hunter.example", "Nova", "Nightingale", [researcher_g])
raven = make_user("raven", "raven@hunter.example", "Raven", "Reyes", [researcher_g])
cipher = make_user("cipher", "cipher@hunter.example", "Kai", "Cipher", [researcher_g])

Company.objects.update_or_create(
    user=acme,
    defaults=dict(
        company_name="Acme Corp",
        website="https://acme.example",
        description="Acme builds the web platform powering 2M+ daily users. We take security seriously and reward researchers who help us stay safe.",
        contact_email="security@acme.example",
        industry="E-Commerce",
        country="Austria",
        is_verified=True,
    ),
)
Company.objects.update_or_create(
    user=techflow,
    defaults=dict(
        company_name="TechFlow GmbH",
        website="https://techflow.example",
        description="TechFlow provides API infrastructure for fintech startups across Europe.",
        contact_email="security@techflow.example",
        industry="Fintech",
        country="Germany",
        is_verified=True,
    ),
)

today = timezone.now().date()


def make_program(owner, name, short, desc, min_b, max_b, **extra):
    program, _ = Program.objects.update_or_create(
        company=owner,
        name=name,
        defaults=dict(
            short_description=short,
            description=desc,
            scope_type="public",
            status="active",
            min_bounty=Decimal(min_b),
            max_bounty=Decimal(max_b),
            start_date=today - timedelta(days=60),
            bounty_policy="Bounties are awarded based on CVSS severity and report quality.",
            testing_guidelines="No automated scanners against production. Use test accounts only. No social engineering or physical attacks.",
            report_guidelines="Include clear reproduction steps, impact assessment, and a proof of concept where possible.",
            disclosure_policy="Coordinated disclosure: please allow 90 days before public disclosure.",
            published_at=timezone.now() - timedelta(days=60),
            **extra,
        ),
    )
    return program


p_web = make_program(
    acme, "Acme Web Platform",
    "Find vulnerabilities in our customer-facing web shop and account portal.",
    "In scope: *.acme.example web applications, including the shop checkout flow, "
    "account management, and the seller portal.\n\nOut of scope: third-party services, "
    "rate limiting issues, self-XSS.",
    "100.00", "5000.00",
)
p_mobile = make_program(
    acme, "Acme Mobile App",
    "Our iOS & Android shopping apps — API and client-side issues welcome.",
    "In scope: the Acme mobile apps (iOS/Android) and the mobile API gateway at "
    "api.acme.example.\n\nOut of scope: issues requiring a rooted/jailbroken device.",
    "50.00", "2500.00",
)
p_api = make_program(
    techflow, "TechFlow API Security",
    "Harden the payment API used by 40+ fintech startups. Top payouts for auth bypasses.",
    "In scope: api.techflow.example (REST + webhooks), OAuth2 flows, and the developer "
    "dashboard.\n\nOut of scope: sandbox environment, documentation site.",
    "200.00", "10000.00",
)

now = timezone.now()
reports_spec = [
    # (reporter, program, title, severity, status, vuln_type, url, cvss_score, cvss_sev, bounty, days_ago)
    (parsa, p_web, "Stored XSS in product review comments", "high", "resolved",
     "Cross-Site Scripting (XSS)", "https://acme.example/products/123/reviews", 8.1, "High", "1500.00", 42),
    (parsa, p_api, "JWT signature not validated on webhook endpoints", "critical", "accepted",
     "Authentication Bypass", "https://api.techflow.example/v2/webhooks", 9.8, "Critical", "8000.00", 21),
    (parsa, p_mobile, "API key leaked in Android APK resources", "medium", "triaged",
     "Information Disclosure", "https://api.acme.example/mobile", 6.5, "Medium", None, 5),
    (nova, p_web, "IDOR allows reading other users' invoices", "high", "accepted",
     "Insecure Direct Object Reference", "https://acme.example/account/invoices", 7.7, "High", "2000.00", 30),
    (nova, p_api, "Race condition in payment idempotency check", "critical", "resolved",
     "Business Logic", "https://api.techflow.example/v2/payments", 9.1, "Critical", "9500.00", 18),
    (raven, p_web, "CSRF on email change endpoint", "medium", "accepted",
     "Cross-Site Request Forgery", "https://acme.example/account/email", 6.8, "Medium", "500.00", 25),
    (raven, p_mobile, "Certificate pinning bypass via debug flag", "low", "rejected",
     "Security Misconfiguration", "https://api.acme.example/mobile", 3.1, "Low", None, 12),
    (cipher, p_api, "SQL injection in transaction search filter", "critical", "triaged",
     "SQL Injection", "https://api.techflow.example/v2/transactions", 9.4, "Critical", None, 2),
    (cipher, p_web, "Open redirect on login return_url parameter", "low", "open",
     "Open Redirect", "https://acme.example/login", 4.3, "Low", None, 1),
    (nova, p_web, "Reflected XSS in search results page", "medium", "open",
     "Cross-Site Scripting (XSS)", "https://acme.example/search", 5.4, "Medium", None, 0),
]

dup_source = None
for reporter, program, title, severity, status, vtype, url, cvss, cvss_sev, bounty, days_ago in reports_spec:
    report, created = BugReport.objects.get_or_create(
        title=title,
        program=program,
        defaults=dict(
            reporter=reporter,
            description=f"While testing {program.name}, I discovered a {severity}-severity "
                        f"{vtype.lower()} issue. Full details and proof of concept below.",
            steps_to_reproduce="1. Log in with a test account\n2. Navigate to the affected "
                               "endpoint\n3. Submit the crafted payload (see PoC)\n4. Observe "
                               "the unauthorized behavior",
            impact="An attacker could exploit this to compromise user data or escalate "
                   "privileges. See CVSS vector for the full impact assessment.",
            severity=severity,
            status=status,
            vulnerability_type=vtype,
            affected_url=url,
            cvss_score=cvss,
            cvss_severity=cvss_sev,
            bounty_amount=Decimal(bounty) if bounty else None,
            assigned_to=triager if status not in ("open",) else None,
        ),
    )
    if created:
        BugReport.objects.filter(pk=report.pk).update(created_at=now - timedelta(days=days_ago))
    if title.startswith("Stored XSS"):
        dup_source = report

# One duplicate report so the duplicate-detection feature has something to show
if dup_source:
    dup, created = BugReport.objects.get_or_create(
        title="XSS in review section (script tag in comment)",
        program=p_web,
        defaults=dict(
            reporter=raven,
            description="Posting a review containing a script tag executes JavaScript for "
                        "every visitor of the product page.",
            steps_to_reproduce="1. Open any product page\n2. Post a review containing "
                               "<script>alert(1)</script>\n3. Reload the page",
            impact="JavaScript execution in victims' browsers.",
            severity="high",
            status="duplicate",
            vulnerability_type="Cross-Site Scripting (XSS)",
            affected_url="https://acme.example/products/123/reviews",
            duplicate_of=dup_source,
            duplicate_reason="Same root cause as the earlier stored XSS report on product reviews.",
            assigned_to=triager,
        ),
    )
    if created:
        BugReport.objects.filter(pk=dup.pk).update(created_at=now - timedelta(days=40))

print("Seeded:")
print(f"  users:    {User.objects.count()}")
print(f"  companies:{Company.objects.count()}")
print(f"  programs: {Program.objects.count()}")
print(f"  reports:  {BugReport.objects.count()}")
print("All demo accounts use password: Demo1234!")
