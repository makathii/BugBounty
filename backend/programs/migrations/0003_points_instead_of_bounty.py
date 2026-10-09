from django.db import migrations, models


class Migration(migrations.Migration):
    """Bounties (money) become points: field renames keep existing rows; dollar ranges are
    reset because dollars do not convert to points."""

    dependencies = [
        ("programs", "0002_perf_indexes"),
    ]

    operations = [
        migrations.RenameField("program", "bounty_policy", "reward_notes"),
        migrations.RemoveField("program", "min_bounty"),
        migrations.RemoveField("program", "max_bounty"),
        migrations.AddField("program", "min_points",
                            models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField("program", "max_points",
                            models.PositiveIntegerField(blank=True, null=True)),
        migrations.RemoveField("program", "total_bounties"),
        migrations.AddField("program", "total_points", models.IntegerField(default=0)),
        migrations.RemoveField("programstats", "total_bounties"),
        migrations.RemoveField("programstats", "avg_bounty"),
        migrations.AddField("programstats", "total_points", models.IntegerField(default=0)),
        migrations.AddField("programstats", "avg_points", models.FloatField(default=0)),
        migrations.RenameField("programstats", "avg_time_to_bounty", "avg_time_to_award"),
        migrations.RenameField("scope", "bounty_multiplier", "points_multiplier"),
        migrations.AlterField(
            model_name="programnotification",
            name="notification_type",
            field=models.CharField(choices=[
                ('new_report', 'New Report'), ('report_status_change', 'Report Status Change'),
                ('program_update', 'Program Update'), ('new_scope', 'New Scope Added'),
                ('points_awarded', 'Points Awarded'), ('application_update', 'Application Status Update'),
                ('invitation', 'New Invitation')], max_length=50),
        ),
    ]
