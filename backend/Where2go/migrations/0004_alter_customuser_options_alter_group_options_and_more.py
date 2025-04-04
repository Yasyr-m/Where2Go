# Generated by Django 4.2.19 on 2025-03-25 09:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('Where2go', '0003_group'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customuser',
            options={'verbose_name': 'Пользователь', 'verbose_name_plural': 'Пользователи'},
        ),
        migrations.AlterModelOptions(
            name='group',
            options={'ordering': ['-created_at'], 'verbose_name': 'Группа', 'verbose_name_plural': 'Группы'},
        ),
        migrations.AddField(
            model_name='group',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='group',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Описание'),
        ),
        migrations.AlterField(
            model_name='group',
            name='admin',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_groups', to=settings.AUTH_USER_MODEL, verbose_name='Администратор'),
        ),
        migrations.AlterField(
            model_name='group',
            name='members',
            field=models.ManyToManyField(related_name='member_groups', to=settings.AUTH_USER_MODEL, verbose_name='Участники'),
        ),
        migrations.AlterField(
            model_name='group',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Название группы'),
        ),
    ]
