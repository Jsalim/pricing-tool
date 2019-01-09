# Generated by Django 2.1.4 on 2019-01-09 21:38

from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0012_auto_20190109_2020'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='modelfeature',
            options={'ordering': [django.db.models.functions.text.Lower('feature__name')]},
        ),
        migrations.AddField(
            model_name='model',
            name='max_nb_features',
            field=models.PositiveSmallIntegerField(default=20),
        ),
    ]
