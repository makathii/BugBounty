# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_bugreport_severity_score_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bugreport',
            name='steps_to_reproduce',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bugreport',
            name='impact',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bugreport',
            name='vulnerability_type',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='bugreport',
            name='affected_url',
            field=models.URLField(blank=True),
        ),
    ]
