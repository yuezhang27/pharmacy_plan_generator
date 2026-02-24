# Generated manually for LLM provider selection

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("careplan", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="careplan",
            name="llm_provider",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
