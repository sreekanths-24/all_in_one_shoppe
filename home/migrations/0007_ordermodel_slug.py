# Generated by Django 3.2.25 on 2024-03-23 02:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_auto_20240323_0749'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordermodel',
            name='slug',
            field=models.SlugField(null=True),
        ),
    ]
