from django.db import migrations, models


class Migration(migrations.Migration):
    """Replace the dollar ``bounty_amount`` with points: ``bonus_points`` is extra points on
    top of the severity points. Old dollar amounts have no points equivalent, so they are dropped."""

    dependencies = [
        ("reports", "0003_comment_threads"),
    ]

    operations = [
        migrations.AddField(
            model_name="bugreport",
            name="bonus_points",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RemoveField(
            model_name="bugreport",
            name="bounty_amount",
        ),
    ]
