# Generated by Django 2.2.2 on 2019-10-06 06:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Kaldi_speech', '0028_auto_20191003_1455'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userverb',
            name='audio',
        ),
        migrations.RemoveField(
            model_name='userverb',
            name='score',
        ),
    ]
