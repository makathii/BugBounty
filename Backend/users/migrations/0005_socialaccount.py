"""Add SocialAccount for OAuth client login (GitHub/Google/GitLab)."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_accountlockout_backupcode_passwordresettoken_usermfa_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('github', 'GitHub'), ('google', 'Google'), ('gitlab', 'GitLab')], max_length=20)),
                ('provider_uid', models.CharField(db_index=True, max_length=128)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('raw_profile', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_login_at'],
                'unique_together': {('provider', 'provider_uid')},
            },
        ),
    ]
