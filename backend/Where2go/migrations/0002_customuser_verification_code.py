# Generated by Django 4.2.19 on 2025-03-13 10:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Where2go', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='verification_code',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
