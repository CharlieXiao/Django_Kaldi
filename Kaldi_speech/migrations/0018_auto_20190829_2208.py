# Generated by Django 2.2.4 on 2019-08-29 14:08

import Kaldi_speech.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Kaldi_speech', '0017_auto_20190829_2147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='course_img',
            field=models.ImageField(default='default/default.png', upload_to=Kaldi_speech.models.course_directory_path, verbose_name='poster'),
        ),
        migrations.AlterField(
            model_name='everydaymotto',
            name='poster',
            field=models.ImageField(default='default/default.png', upload_to='motto/poster', verbose_name='poster'),
        ),
        migrations.AlterField(
            model_name='verb',
            name='uk_speech',
            field=models.FileField(default='default/default.wav', upload_to='verb/', verbose_name='uk speech'),
        ),
        migrations.AlterField(
            model_name='verb',
            name='us_phonetic',
            field=models.CharField(max_length=100, verbose_name='us phonetic'),
        ),
    ]