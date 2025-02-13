from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from datetime import date
from .models import Cart, CartItem,Wishlist
from product.models import Product
from django.http import JsonResponse
import json
from decimal import Decimal
from django.db import transaction
from .models import Users, Order
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from payment.models import OrderProduct,Wallet, WalletTransaction
from django.views.decorators.cache import never_cache
from payment.models import Coupon






@login_required(login_url="user_login")
def add_to_cart(request, product_id):
    if request.method == "POST":
        try:
            
            body = json.loads(request.body)
            quantity = int(body.get('quantity', 1))  
            
          
            if quantity <= 0:
                return JsonResponse({'error': 'Quantity must be greater than 0'}, status=400)
            
            
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                is_active=True
            )
            
            
            product = get_object_or_404(Product, id=product_id)
            
            with transaction.atomic():
               
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': 0}  
                )
                
               
                new_quantity = cart_item.quantity + quantity
                
               
                if new_quantity > 5:
                    return JsonResponse({
                        'error': 'Maximum 5 items allowed per product'
                    }, status=400)
                
                if new_quantity > product.stock_count:
                    return JsonResponse({
                        'error': f'Only {product.stock_count} items available in stock'
                    }, status=400)
                
               
                cart_item.quantity = new_quantity
                cart_item.save()
                
               
                cart_subtotal = cart.subtotal()
                cart_tax = cart.calculate_tax()
                cart_total = cart_subtotal + cart_tax
                
                return JsonResponse({
                    'success': True,
                    'message': 'Product added to cart',
                    'cart_summary': {
                        'subtotal': float(cart_subtotal),
                        'tax': float(cart_tax),
                        'total': float(cart_total),
                        'quantity': new_quantity
                    }
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid request format'}, status=400)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)





def user_cart(request):
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = cart.items.all()
        
        if not cart_items.exists():
            return render(request, 'user/user_cart.html', {
                'message': 'Your cart is empty.',
                'is_empty': True
            })
            
        cart_subtotal = 0
        cart_discount = 0

        for item in cart_items:
            product = item.product
            original_price = product.price

            if product.is_offer_applied and product.discount_percentage:
                discount_amount = (product.discount_percentage / 100) * original_price
                discounted_price = original_price - discount_amount
            else:
                discounted_price = original_price
            
            item.discounted_price = discounted_price  
            item.save()

            cart_subtotal += discounted_price * item.quantity
            cart_discount += discount_amount * item.quantity if product.is_offer_applied else 0

        cart_tax = cart.calculate_tax()
        cart_total = cart_subtotal + cart_tax

        context = {
            'cart': cart,
            'cart_items': cart_items,
            'cart_subtotal': cart_subtotal,
            'cart_tax': cart_tax,
            'cart_discount': cart_discount,  
            'cart_total': cart_total,
            'is_empty': False
        }
        
    except Cart.DoesNotExist:
        context = {
            'message': 'Your cart is empty.',
            'is_empty': True
        }
        
    return render(request, 'user/user_cart.html', context)




@login_required(login_url="login")
def update_cart_item(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
        
    try:
        data = json.loads(request.body)
        product_id = data.get('productId')
        new_quantity = int(data.get('quantity', 1))
        
        if new_quantity <= 0:
            return JsonResponse({'error': 'Quantity must be greater than 0'}, status=400)
            
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        product = get_object_or_404(Product, id=product_id)
        
        if new_quantity > min(product.stock_count, 5):
            return JsonResponse({
                'error': f'Only {min(product.stock_count, 5)} items allowed'
            }, status=400)
            
        with transaction.atomic():
            cart_item, _ = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': new_quantity}
            )
            
            if not _:  
                cart_item.quantity = new_quantity
                cart_item.save()
                
            original_price = product.price
            discount_amount = (product.discount_percentage / 100) * original_price if product.is_offer_applied else 0
            discounted_price = original_price - discount_amount

            subtotal = discounted_price * cart_item.quantity
            cart_subtotal = sum(
                (item.product.price - ((item.product.discount_percentage / 100) * item.product.price) if item.product.is_offer_applied else item.product.price) * item.quantity
                for item in cart.items.all()
            )
            
            cart_discount = sum(
                ((item.product.discount_percentage / 100) * item.product.price * item.quantity) if item.product.is_offer_applied else 0
                for item in cart.items.all()
            )

            cart_tax = cart.calculate_tax()
            cart_total = cart_subtotal + cart_tax

            return JsonResponse({
                'success': True,
                'new_quantity': cart_item.quantity,
                'subtotal': float(subtotal),
                'cart_summary': {
                    'subtotal': float(cart_subtotal),
                    'discount': float(cart_discount),  
                    'tax': float(cart_tax),
                    'total': float(cart_total)
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request format'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)






@login_required(login_url="login")
def delete_from_cart(request, product_id):
    user = request.user

    try:
        with transaction.atomic():
            user_cart = get_object_or_404(Cart, user=user, is_active=True)
            cart_item = get_object_or_404(CartItem, cart=user_cart, product_id=product_id)

            cart_item.delete()
            product = get_object_or_404(Product, id=product_id)
            product.stock_count += cart_item.quantity
            product.save()

            new_subtotal = user_cart.subtotal()  
            
           
            return JsonResponse({
                'success': True,
                'message': 'Product removed from cart',
                'new_subtotal': new_subtotal
            })

    except (CartItem.DoesNotExist, Product.DoesNotExist):
        return JsonResponse({'error': 'Item or product not found'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)






@login_required(login_url="user_login")
def wishlist_view(request, product_id):
    if request.method == "POST":
        try:
            product = get_object_or_404(Product, id=product_id)
            wishlist_item = Wishlist.objects.filter(user=request.user, product=product)
            
            if wishlist_item.exists():
                wishlist_item.delete()
                message = 'Product removed from wishlist'
            else:
                Wishlist.objects.create(user=request.user, product=product)
                message = 'Product added to wishlist'
                
            return JsonResponse({
                'success': True,
                'message': message
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@login_required(login_url="user_login")
def wishlist(request):
    wishlist_products = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_products': wishlist_products
    }
    return render(request, 'user/wishlist.html', context)
from django.http import JsonResponse



@login_required(login_url="user_login")
def add_to_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

        if not created:
            wishlist_item.delete()
            return JsonResponse({"success": True, "message": "Product removed from wishlist"})

        return JsonResponse({"success": True, "message": "Product added to wishlist"})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})




@login_required(login_url="user_login")
def remove_from_wishlist(request, product_id):
    try:
        wishlist_item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
        wishlist_item.delete()
        messages.success(request, 'Product removed from wishlist')
        
    except Wishlist.DoesNotExist:
        messages.error(request, 'Product not found in wishlist')
        
    return redirect('wishlist')





@login_required(login_url="user_login")
def wishlist_to_cart(request, product_id):
    try:
        with transaction.atomic():
            wishlist_item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
            product = wishlist_item.product
            
            if product.stock_count <= 0:
                messages.error(request, 'Product is out of stock')
                return redirect('wishlist')
            
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                is_active=True
            )
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 1} 
            )
            
            if not created:
                if cart_item.quantity >= 5:  
                    messages.error(request, 'Maximum quantity limit reached for this product')
                    return redirect('wishlist')
                cart_item.quantity += 1 
                cart_item.save()
            
            wishlist_item.delete()
            
            messages.success(request, 'Product moved to cart successfully')
            
    except Exception as e:
        messages.error(request, f'Error moving product to cart: {str(e)}')
        
    return redirect('wishlist')



@login_required(login_url="user_login")
def get_wishlist_count(request):
    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})






@login_required
def user_account(request):
    user = request.user

    orders_list = Order.objects.filter(user=user).order_by('-created_at')

    order_status_counts = {
        "pending": orders_list.filter(shipping_status="Pending").count(),
        "shipped": orders_list.filter(shipping_status="Shipped").count(),
        "delivered": orders_list.filter(shipping_status="Delivered").count(),
        "cancelled": orders_list.filter(shipping_status="Cancelled").count(),
        "returned": orders_list.filter(shipping_status="Returned").count(),
    }

    page = request.GET.get('page', 1)
    paginator = Paginator(orders_list, 5)

    try:
        orders = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        orders = paginator.page(1) 

    context = {
        'user': user,
        'orders': orders,
        **order_status_counts,  
    }

    if 'error_message' in request.session:
        messages.error(request, request.session.pop('error_message'))

    return render(request, 'user/user_account.html', context)



def get_valid_status_transitions(current_status):
    transitions = {
        'Pending': ['Shipped', 'Cancelled'],
        'Shipped': ['Delivered', 'Cancelled'],
        'Delivered': [],  # No further transitions allowed
        'Cancelled': []   # No further transitions allowed
    }
    return transitions.get(current_status, [])


# Admin side
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)



@never_cache
@login_required(login_url='admin_login')
@admin_required
def admin_user_order_management(request):
    users = Users.objects.all().order_by('username')
    selected_user_id = request.GET.get('user_id')
    orders = []
    selected_user = None

    if selected_user_id:
        try:
            selected_user = Users.objects.get(id=selected_user_id)
            orders = Order.objects.filter(user=selected_user).order_by('-created_at')
        except (Users.DoesNotExist, ValueError):
            messages.error(request, "Invalid user selection.")

    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)
    
    try:
        orders_paginated = paginator.page(page)
    except PageNotAnInteger:
        orders_paginated = paginator.page(1)
    except EmptyPage:
        orders_paginated = paginator.page(paginator.num_pages)

    context = {
        'orders': orders_paginated,
        'users': users,
        'selected_user': selected_user,
    }
    return render(request, 'admin_page/order_management.html', context)




def update_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    selected_user_id = request.POST.get('user_id')

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_status":
            new_status = request.POST.get("status")
            valid_transitions = get_valid_status_transitions(order.shipping_status)

            if new_status in valid_transitions:
                order.shipping_status = new_status
                order.save()
                messages.success(request, f"Order #{order_id} shipping status updated to {new_status}.")
            else:
                messages.error(request, f"Invalid status transition from {order.shipping_status} to {new_status}.")

        elif action == "cancel_order":
            if order.shipping_status not in ["Delivered", "Cancelled"]:
                order.shipping_status = "Cancelled"
                order.save()
                messages.success(request, f"Order #{order_id} has been cancelled.")
            else:
                messages.error(request, f"Order #{order_id} cannot be cancelled because it's {order.shipping_status}.")

    return redirect(f"/cart/admin/order-management/?user_id={selected_user_id}")



def calculate_product_totals(product, applied_coupon=None):
    base_price = product.price
    discount_amount = Decimal('0.00')


    if applied_coupon:
        discount_amount = (Decimal(applied_coupon.discount_percentage) / 100) * base_price
        base_price -= discount_amount

    tax_rate = Decimal('0.001')
    tax_amount = base_price * tax_rate
    final_price = base_price + tax_amount

    
    return base_price, discount_amount, tax_amount, final_price



def order_details_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_products = OrderProduct.objects.filter(order=order)

    subtotal = Decimal('0.00')
    total_discount = Decimal('0.00')
    total_tax = Decimal('0.00')
    final_order_total = Decimal('0.00')


    for item in order_products:
        base_price, discount_amount, tax_amount, final_price = calculate_product_totals(
            item.product, applied_coupon=order.coupon
        )


        subtotal += base_price
        total_discount += discount_amount
        total_tax += tax_amount
        final_order_total += final_price


    context = {
        "order": order,
        "order_products": order_products,
        "subtotal": subtotal,
        "discount": total_discount,  
        "total_tax": total_tax,
        "final_order_total": final_order_total,
    }

    return render(request, "user/order_details.html", context)







@login_required(login_url='user_login')
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'Pending':
        new_status = 'Cancelled' 
        success_message = 'Your order has been cancelled successfully'
        wallet ,created = Wallet.objects.get_or_create(user=request.user)
        wallet.add_amount(order.total_amount)
        
        WalletTransaction.objects.create(
            wallet = wallet,
            transaction_type = 'CANCELED_ORDER',
            amount = order.total_amount
        )
    elif order.status == 'Delivered':
        new_status = 'Returned'  
        success_message = 'Your order has been returned successfully'
        wallet ,created =Wallet.objects.get_or_create(user =request.user)
        wallet.add_amount(order.total_amount)
        
        WalletTransaction.objects.create(
            wallet = wallet,
            transaction_type = 'RETURNED_ORDER',
            amount =order.total_amount
        )
    else:
        messages.error(request, 'This action is not allowed for the current order status')
        return redirect('order_details', order_id=order.id)

    try:
        with transaction.atomic():
            order.status = new_status
            order.shipping_status = new_status 
            order.save()
            messages.success(request, success_message)
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')

    return redirect('order_details', order_id=order.id)







def wallet_view(request):
    if not request.user.is_authenticated:
        return redirect('login')  

    wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})

    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')

    return render(request, 'user/wallet.html', {'wallet': wallet, 'transactions': transactions})
