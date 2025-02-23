# Generated by Django 5.1.5 on 2025-02-05 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0004_wallet_wallettransaction'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallettransaction',
            name='description',
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_type',
            field=models.CharField(choices=[('CANCELLED_ORDER', 'Cancelled Order Refund'), ('RETURNED_ORDER', 'Returned Order Refund')], max_length=20),
        ),
    ]
