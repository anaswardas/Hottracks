# Generated by Django 5.1.5 on 2025-02-04 04:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_payment_payment_gateway_payment_payment_method_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='razorpay_signature',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_gateway',
            field=models.CharField(default='RAZORPAY', max_length=100),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('RAZORPAY', 'Razorpay'), ('CASH', 'Cash'), ('CARD', 'Card')], default='RAZORPAY', max_length=50),
        ),
    ]
