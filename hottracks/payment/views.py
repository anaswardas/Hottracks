from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from cart.models import Cart, Order, CartItem
from accounts.models import Address
from payment.models import Payment, OrderProduct,Wallet,WalletTransaction,Coupon,CouponUsage
from decimal import Decimal
import uuid
from django.db import transaction
from django.http import JsonResponse
import hmac
import hashlib
from django.shortcuts import get_object_or_404
from .models import Order
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
import razorpay
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from datetime import datetime
from django.utils.timezone import now
from django.http import HttpResponseRedirect
from django.db import models
from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from datetime import datetime, timedelta




def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)

@never_cache
@login_required(login_url='admin_login')
@admin_required
def admin_coupon_view(request):
    coupons = Coupon.objects.all()
    return render(request,'admin_page/admin_coupon.html',{'coupons' : coupons})





@never_cache
@login_required(login_url='admin_login')
@admin_required
def add_coupon(request):
    errors = []
    
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code', '').strip()
        title = request.POST.get('title', '').strip()
        discount_percentage = request.POST.get('discount_percentage', '0').strip()
        start_date_str = request.POST.get('start_date', '').strip()
        end_date_str = request.POST.get('end_date', '').strip()
        is_active = request.POST.get('active') == 'on'

    
        if not coupon_code or not title:
            errors.append("Title and Coupon Code are required.")

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            errors.append("Invalid start date format.")

        
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                if end_date <= start_date:
                    errors.append("End date must be after the start date.")
            except ValueError:
                errors.append("Invalid end date format.")

        try:
            discount_percentage = Decimal(discount_percentage)
            if not (1 <= discount_percentage <= 50):
                errors.append("Discount percentage must be between 1 and 50.")
        except InvalidOperation:
            errors.append("Invalid discount percentage format.")

        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            errors.append("Quantity must be a valid integer.")

        try:
            min_amount = Decimal(request.POST.get('min_amount', '0'))
            max_amount = Decimal(request.POST.get('max_amount', '0'))
        except InvalidOperation:
            errors.append("Invalid minimum or maximum amount.")


        if not errors:
            if Coupon.objects.filter(code=coupon_code).exists():
                messages.error(request, "Coupon code already exists.")
            else:
                Coupon.objects.create(
                    title=title,
                    code=coupon_code,
                    discount_percentage=discount_percentage,
                    start_date=start_date,
                    end_date=end_date,
                    quantity=quantity,
                    min_amount=min_amount,
                    max_amount=max_amount,
                    is_active=is_active
                )
                messages.success(request, "Coupon added successfully.")
                return redirect('admin_coupon') 

    return render(request, 'admin_page/add_coupon.html', {'messages': errors})




@never_cache
@login_required(login_url='admin_login')
@admin_required
def edit_coupon(request,coupon_id):
    
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        coupon_code = request.POST.get('coupon_code', '').strip()
        discount_percentage = request.POST.get('discount_percentage', '0').strip()
        start_date_str = request.POST.get('start_date', '').strip()
        end_date_str = request.POST.get('end_date', '').strip()
        is_active = request.POST.get('active') == 'on'
        
        
        errors = []
        if not coupon_code or not title:
            errors.append("Title and Coupon Code are required.")

       
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            errors.append("Invalid start date format.")
            
            
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                if end_date <= start_date:
                    errors.append("End date must be after the start date.")
            except ValueError:
                errors.append("Invalid end date format.")
             
                
        try:
            discount_percentage = Decimal(discount_percentage)
            if not (1 <= discount_percentage <= 50):
                errors.append("Discount percentage must be between 1 and 50.")
        except ValueError:
            errors.append("Invalid discount percentage format.")

        
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            errors.append("Quantity must be a valid integer.")

       
        try:
            min_amount = Decimal(request.POST.get('min_amount', '0'))
            max_amount = Decimal(request.POST.get('max_amount', '0'))
        except ValueError:
            errors.append("Invalid minimum or maximum amount.")

        
        if not errors:
            coupon.title = title
            coupon.code = coupon_code
            coupon.discount_percentage = discount_percentage
            coupon.start_date = start_date
            coupon.end_date = end_date
            coupon.quantity = quantity
            coupon.min_amount = min_amount
            coupon.max_amount = max_amount
            coupon.is_active = is_active
            coupon.save()

            messages.success(request, "Coupon updated successfully.")
            return redirect('admin_coupon')  
    return render(request, 'admin_page/edit_coupon.html', {'coupon': coupon})



@never_cache
@login_required(login_url='admin_login')
@admin_required
def coupon_status(request,coupon_id):
    coupon = get_object_or_404(Coupon, id = coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save()
    
    status = 'activated' if coupon.is_active else 'deactivated'
    messages.success(request, f'Coupon  {status} Successfully')
    
    return HttpResponseRedirect(reverse('admin_coupon'))





@login_required
@require_POST
def apply_coupon(request):
    try:
        data = json.loads(request.body)
        coupon_code = data.get("coupon_code", "").strip()
        
        if not coupon_code:
            return JsonResponse({
                "status": "error", 
                "message": "Please enter a coupon code"
            }, status=400)

        
        try:
            cart = Cart.objects.get(user=request.user, is_active=True)
        except Cart.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "No active cart found"
            }, status=400)

        
        subtotal = cart.subtotal()
        tax = cart.calculate_tax()
        total_price = subtotal + tax

      
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            
            
            if not coupon.is_valid(request.user):
                return JsonResponse({
                    "status": "error",
                    "message": "This coupon is no longer valid"
                }, status=400)

        
            if coupon.quantity <= CouponUsage.objects.filter(coupon=coupon).count():
                return JsonResponse({
                    "status": "error",
                    "message": "This coupon has reached its usage limit"
                }, status=400)

           
            if total_price < coupon.min_amount:
                return JsonResponse({
                    "status": "error",
                    "message": f"Minimum order amount of ₹{coupon.min_amount} required for this coupon"
                }, status=400)

           
            if coupon.max_amount > 0 and total_price > coupon.max_amount:
                return JsonResponse({
                    "status": "error",
                    "message": f"This coupon is valid only for orders up to ₹{coupon.max_amount}"
                }, status=400)

           
            if coupon.start_date and coupon.start_date > now():
                return JsonResponse({
                    "status": "error",
                    "message": "This coupon is not yet active"
                }, status=400)

          
            if coupon.end_date and coupon.end_date < now():
                return JsonResponse({
                    "status": "error",
                    "message": "This coupon has expired"
                }, status=400)

        except Coupon.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Invalid coupon code"
            }, status=400)

      
        final_total = coupon.apply_discount(total_price, request.user)
        discount_amount = total_price - final_total

        
        request.session['applied_coupon'] = {
            'code': coupon.code,
            'discount_percentage': float(coupon.discount_percentage),
            'title': coupon.title
        }
        request.session.modified = True

        return JsonResponse({
            "status": "success",
            "coupon_code": coupon.code,
            "coupon_title": coupon.title,
            "discount": float(coupon.discount_percentage),
            "discount_amount": float(discount_amount),
            "final_total": float(final_total),
            "message": f"Coupon '{coupon.title}' applied successfully!"
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid request format"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": "An unexpected error occurred"
        }, status=500)
        
        
@login_required
@require_POST
def remove_coupon(request):
    try:
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        final_total = cart.subtotal() + cart.calculate_tax()

        # Remove coupon from session
        request.session.pop('applied_coupon', None)
        request.session.modified = True

        return JsonResponse({
            'status': 'success',
            'message': 'Coupon removed successfully',
            'final_total': float(final_total)
        })

    except Cart.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'No active cart found'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }, status=500)



def calculate_total_price(user, coupon_code=None):
    cart = get_object_or_404(Cart, user=user, is_active=True)
    subtotal = cart.subtotal()
    tax = cart.calculate_tax()
    total_price = subtotal + tax
    discount_amount = 0

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            
            
            if CouponUsage.objects.filter(user=user, coupon=coupon).exists():
                return total_price, 0  

            if coupon.is_valid(user):
                discount_amount = (coupon.discount_percentage / 100) * total_price
                total_price -= discount_amount
        except Coupon.DoesNotExist:
            pass

    return total_price, discount_amount




@login_required(login_url='user_login')
def checkout_view(request):
    try:
        
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = cart.items.all()

        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart_view')
    except Cart.DoesNotExist:
        messages.error(request, "No active cart found.")
        return redirect('cart_view')

   
    subtotal = cart.subtotal()
    tax = cart.calculate_tax()
    total_price = subtotal + tax

    current_time = now()
    applied_coupon = None
    discount_amount = Decimal('0.00')

  
    if 'applied_coupon' in request.session and request.session.get('coupon_applied_once', False) == False:
        coupon_code = request.session['applied_coupon']['code']
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                is_active=True,
                start_date__lte=current_time
            )

            # Validate the coupon
            if coupon.end_date and coupon.end_date < current_time:
                raise ValueError("This coupon has expired.")
            if coupon.quantity <= CouponUsage.objects.filter(coupon=coupon).count():
                raise ValueError("This coupon has reached its usage limit.")
            if total_price < coupon.min_amount:
                raise ValueError(f"Minimum order amount of ₹{coupon.min_amount} required for this coupon.")
            if coupon.max_amount > 0 and total_price > coupon.max_amount:
                raise ValueError(f"This coupon is valid only for orders up to ₹{coupon.max_amount}.")

            # Calculate the discount
            applied_coupon = coupon
            discount_amount = coupon.apply_discount(total_price, request.user)
            total_price -= discount_amount

            request.session['coupon_applied_once'] = True

        except (Coupon.DoesNotExist, ValueError) as e:
            del request.session['applied_coupon']
            messages.warning(request, str(e))

    # Get available coupons for the user
    used_coupons = CouponUsage.objects.filter(user=request.user).values_list('coupon_id', flat=True)
    available_coupons = Coupon.objects.annotate(
        usage_count=models.Count('coupon_usage')
    ).filter(
        is_active=True,
        start_date__lte=current_time,
        quantity__gt=models.F('usage_count'),
        min_amount__lte=total_price
    ).exclude(
        id__in=used_coupons
    ).exclude(
        end_date__lt=current_time
    )

    if request.method == 'POST':
        selected_address_id = request.POST.get('selected_address')
        payment_method = request.POST.get('payment_method')
        coupon_code = request.POST.get('coupon_code', '').strip()

        # Validate address and payment method
        if not selected_address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('checkout_view')
        if payment_method not in ['COD', 'Razorpay']:
            messages.error(request, "Invalid payment method selected.")
            return redirect('checkout_view')

        try:
            with transaction.atomic():
                # Get the selected address
                address = get_object_or_404(Address, id=selected_address_id, user=request.user, is_delete=False)

                # Handle coupon validation during POST
                if coupon_code and not applied_coupon:
                    try:
                        coupon = Coupon.objects.get(
                            code=coupon_code,
                            is_active=True,
                            start_date__lte=current_time
                        )

                        # Validate the coupon again
                        if coupon.end_date and coupon.end_date < current_time:
                            raise ValueError("This coupon has expired.")
                        if coupon.quantity <= CouponUsage.objects.filter(coupon=coupon).count():
                            raise ValueError("This coupon has reached its usage limit.")
                        if total_price < coupon.min_amount:
                            raise ValueError(f"Minimum order amount of ₹{coupon.min_amount} required for this coupon.")
                        if coupon.max_amount > 0 and total_price > coupon.max_amount:
                            raise ValueError(f"This coupon is valid only for orders up to ₹{coupon.max_amount}.")

                        # Apply the coupon
                        applied_coupon = coupon
                        discount_amount = coupon.apply_discount(total_price, request.user)
                        total_price -= discount_amount
                        request.session['applied_coupon'] = {
                            'code': coupon.code,
                            'title': coupon.title,
                            'discount_percentage': float(coupon.discount_percentage)
                        }
                    except (Coupon.DoesNotExist, ValueError) as e:
                        messages.error(request, str(e))
                        return redirect('checkout_view')

                # Create Payment
                payment = Payment.objects.create(
                    user=request.user,
                    amount=total_price,
                    status='Pending',
                    payment_method=payment_method
                )

                # Create Order
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_method=payment_method,
                    total_amount=total_price,
                    status='Pending',
                    payment=payment,
                    coupon=applied_coupon
                )

                # Record coupon usage
                if applied_coupon:
                    CouponUsage.objects.create(
                        user=request.user,
                        coupon=applied_coupon
                    )
                    messages.success(request, f"Coupon '{applied_coupon.title}' applied successfully!")

                # Handle COD
                if payment_method == 'COD':
                    payment.payment_method = 'CASH'
                    payment.status = 'Completed'
                    payment.save()
                    cart_cleanup(request.user, cart_items, order)
                    request.session.pop('applied_coupon', None)
                    request.session.pop('coupon_applied_once', None)
                    messages.success(request, "Order placed successfully with Cash on Delivery!")
                    return redirect('checkout_success')

                # Handle Razorpay
                if payment_method == 'Razorpay':
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    razorpay_order = client.order.create({
                        "amount": int(total_price * 100),
                        "currency": "INR",
                        "payment_capture": "1"
                    })
                    payment.razorpay_order_id = razorpay_order['id']
                    payment.save()

                    context = {
                        'razorpay_order_id': razorpay_order['id'],
                        'razorpay_key': settings.RAZORPAY_KEY_ID,
                        'amount': int(total_price * 100),
                        'currency': "INR",
                        'name': request.user.get_full_name() or request.user.username,
                        'email': request.user.email,
                        'order_id': order.id,
                        'applied_coupon': request.session.get('applied_coupon', None),
                    }
                    return render(request, 'user/razorpay_checkout.html', context)

        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
            return redirect('checkout_view')

   
    context = {
        'addresses': Address.objects.filter(user=request.user, is_delete=False),
        'cart_items': cart_items,
        'cart_subtotal': subtotal,
        'cart_tax': tax,
        'cart_total': total_price,
        'coupons': available_coupons if available_coupons.exists() and not applied_coupon else [],
        'applied_coupon': request.session.get('applied_coupon', None),
    }

    return render(request, 'user/user_checkout.html', context)







@login_required(login_url='user_login')
@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        try:
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            razorpay_order_id = request.POST.get('order_id')

            if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                return JsonResponse({"status": "error", "message": "Missing required payment details"})

            try:
                payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            except Payment.DoesNotExist:
                return JsonResponse({"status": "error", "message": f"Payment not found for order ID: {razorpay_order_id}"})

            generated_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
                hashlib.sha256
            ).hexdigest()

            if generated_signature == razorpay_signature:
                with transaction.atomic():
                    payment.status = 'Completed'
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.razorpay_signature = razorpay_signature
                    payment.save()

                    order = Order.objects.get(payment=payment)
                    order.status = 'Confirmed'
                    order.save()

                    try:
                        cart = Cart.objects.get(user=order.user, is_active=True)
                        cart_items = cart.items.all()
                        cart_cleanup(order.user, cart_items, order)

                       
                        if 'applied_coupon' in request.session:
                            del request.session['applied_coupon']

                    except Cart.DoesNotExist:
                        pass

                return JsonResponse({
                    "status": "success",
                    "message": "Payment verified successfully",
                    "redirect_url": reverse('checkout_success')
                })
            else:
                payment.status = 'Failed'
                payment.save()
                return JsonResponse({"status": "error", "message": "Payment signature verification failed"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request method"})





def cart_cleanup(user, cart_items, order):
 
    with transaction.atomic():
       
        for item in cart_items:
            
            OrderProduct.objects.create(
                order=order,
                product=item.product,
                price=item.product.price,
                quantity=item.quantity
            )
            
           
            item.product.stock_count -= item.quantity
            item.product.save()
        
       
        cart = cart_items.first().cart
        cart_items.delete()
        cart.delete()



cart_cleanup


@login_required(login_url="user_login/")
def checkout_success(request):

    return render (request,'user/checkout_success.html')










@never_cache
@login_required(login_url='admin_login')
@admin_required
def sales_report(request):
    report_type = request.GET.get('report_type', 'day')
    
    today = timezone.now().date()
    
    if report_type == 'day':
        start_date = today
        end_date = today
    elif report_type == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif report_type == 'month':
        start_date = today.replace(day=1)
        end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif report_type == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    elif report_type == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            start_date = today
            end_date = today
    else:
        start_date = today
        end_date = today

    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('user', 'payment').prefetch_related('order_products__product')

    order_data = []
    total_sales_amount = 0
    total_discount_amount = 0
    total_final_total = 0

    for order in orders:
        products_data = []
        for order_product in order.order_products.all():
            product_total = order_product.price * order_product.quantity
            product_discount = 0
            if order.coupon:
                product_discount = (product_total * order.coupon.discount_percentage / 100)
            
            product_final_total = product_total - product_discount
            
            products_data.append({
                'product': order_product.product,
                'quantity': order_product.quantity,
                'product_total_amount': product_total,
                'product_discount_amount': product_discount,
                'product_final_total': product_final_total
            })
            
            total_sales_amount += product_total
            total_discount_amount += product_discount
            total_final_total += product_final_total
        
        order_data.append({
            'order': order,
            'products': products_data
        })

    total_order_count = orders.count()
    
    earnings = total_final_total

    context = {
        'orders': order_data,
        'total_order_count': total_order_count,
        'total_sales_amount': total_sales_amount,
        'total_discount_amount': total_discount_amount,
        'total_final_total': total_final_total,
        'earnings': earnings,
        'start_date': start_date,
        'end_date': end_date,
        'report_type': report_type
    }

    return render(request, 'admin_page/sales.html', context)

