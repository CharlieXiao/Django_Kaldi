# Generated by Django 2.2.4 on 2019-08-24 08:48

import Kaldi_speech.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Kaldi_speech', '0006_auto_20190824_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sentence',
            name='sentence_src',
            field=models.FileField(default='/course/default.wav', upload_to=Kaldi_speech.models.section_directory_path, verbose_name='audio'),
        ),
    ]
