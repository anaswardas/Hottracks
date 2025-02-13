from django.shortcuts import render, redirect,get_object_or_404
from .models import Product,Category,Offer
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
import sys
from django.core.paginator import Paginator
from django.db.models import Q,Count
from cart.models import Wishlist
from django.db.models import F, Case, When, DecimalField
from decimal import Decimal


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)


@never_cache
@login_required(login_url='admin_login')
@admin_required
# Category View
def category_view(request):
    categories = Category.objects.all()
    return render(request, 'admin_page/admin_category.html', {'categories': categories})

from django.conf import settings

@never_cache
@login_required(login_url='admin_login')
@admin_required
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name').strip()
        category_description = request.POST.get('description').strip()
        category_image = request.FILES.get('category_image') 
        if category_name:
            if Category.objects.filter(name__iexact=category_name).exists():
                messages.error(request, "Category name already exists (case-insensitive). Please choose another name.")
            else:
                try:
                    category = Category(
                        name=category_name,
                        description=category_description,
                        category_image=category_image  
                    )
                    category.save()
                    messages.success(request, "Category added successfully!")
                    return redirect('admin_category')
                except ValidationError as e:
                    messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Category name is required.")
    return render(request, 'admin_page/add_category.html')




@never_cache
@login_required(login_url='admin_login')
@admin_required
# Edit category
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category_name = request.POST.get('category_name').strip()
        category_description = request.POST.get('category_description').strip()
        category_image = request.FILES.get('category_image')  # Get uploaded image if provided

        if category_name:
            if Category.objects.filter(name__iexact=category_name).exclude(id=category.id).exists():
                messages.error(request, "Category name already exists (case-insensitive). Please choose another name.")
            else:
                category.name = category_name
                category.description = category_description
                
               
                if category_image:
                    category.category_image = category_image
                
                category.save()
                messages.success(request, "Category updated successfully!")
                return redirect('admin_category')
        else:
            return render(request, 'admin_page/edit_category.html', {'category': category, 'error': 'Category name is required.'})

    return render(request, 'admin_page/edit_category.html', {'category': category})




@never_cache
@login_required(login_url='admin_login')
@admin_required
# Category Status
def category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if category.is_active:
        category.unlist()
        messages.success(request, f"Category '{category.name}' has been deactivated.")
    else:
        category.list()
        messages.success(request, f"Category '{category.name}' has been activated.")
    return redirect('admin_category')




@never_cache
@login_required(login_url='admin_login')
@admin_required
# Products View Admin side
def product_view(request):
    products = Product.objects.all()
    return render(request, 'admin_page/admin_products.html', {'products': products})



@never_cache
@login_required(login_url='admin_login')
@admin_required
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name').strip().lower() 
        description = request.POST.get('description').strip()
        price = request.POST.get('price')
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')
        category_id = request.POST.get('category')
        stock_count = request.POST.get('stock_count')

        if not all([name, description, price, category_id, stock_count]):
            messages.error(request, "All fields are required.")
            return redirect('add_product')

        
        try:
            price = float(price)
            if price <= 0:
                messages.error(request, "Price must be a positive number.")
                return redirect('add_product')
        except ValueError:
            messages.error(request, "Invalid price format.")
            return redirect('add_product')

        try:
            category = Category.objects.get(id=category_id)

           
            normalized_name = " ".join(name.split())  
            if Product.objects.filter(name__iexact=normalized_name).exclude(category=category).exists():
                messages.error(request, "A product with this name already exists in another category.")
                return redirect('add_product')

           
            allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
            images = [image1, image2, image3]
            if sum(1 for img in images if img) < 3:
                messages.error(request, "At least 3 images must be uploaded.")
                return redirect('add_product')

            processed_images = []
            for img in images:
                if img:
                    ext = img.name.split('.')[-1].lower()
                    if ext not in allowed_extensions:
                        messages.error(request, f"Invalid file type for {img.name}. Only images are allowed.")
                        return redirect('add_product')
                    
               
                    processed_img = crop_and_resize_image(img)
                    processed_images.append(processed_img)

            product = Product(
                name=normalized_name,
                description=description,
                price=price,
                image1=processed_images[0],
                image2=processed_images[1],
                image3=processed_images[2],
                category=category,
                stock_count=stock_count
            )
            product.save()
            messages.success(request, "Product added successfully!")
            return redirect('admin_products')

        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
        except ValidationError as e:
            messages.error(request, f"Error: {e}")

    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin_page/add_product.html', {'categories': categories})



def crop_and_resize_image(image_file, target_size=(800, 800)):
   
    img = Image.open(image_file)

    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    width, height = img.size
    dimension = min(width, height)

    left = (width - dimension) // 2
    top = (height - dimension) // 2
    right = left + dimension
    bottom = top + dimension

    img = img.crop((left, top, right, bottom))

    img = img.resize(target_size, Image.Resampling.LANCZOS)

    output = BytesIO()
    img.save(output, format='JPEG', quality=90)
    output.seek(0)

    
    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{image_file.name.split('.')[0]}_cropped.jpg",
        'image/jpeg',
        sys.getsizeof(output),
        None
    )



@never_cache
@login_required(login_url='admin_login')
@admin_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        name = request.POST.get('name', product.name).strip()
        description = request.POST.get('description', product.description).strip()
        price = request.POST.get('price', product.price)
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')
        category_id = request.POST.get('category', product.category.id)
        stock_count = request.POST.get('stock_count', product.stock_count)

        if not all([name, description, price, category_id, stock_count]):
            messages.error(request, "All fields are required.")
            return redirect('edit_product', product_id=product.id)

        try:
            price = float(price)
            if price <= 0:
                messages.error(request, "Price must be a positive number.")
                return redirect('edit_product', product_id=product.id)
        except ValueError:
            messages.error(request, "Invalid price format.")
            return redirect('edit_product', product_id=product.id)

        try:
            category = Category.objects.get(id=category_id)

            if Product.objects.filter(name=name).exclude(id=product.id).exclude(category=category).exists():
                messages.error(request, "A product with this name already exists in another category.")
                return redirect('edit_product', product_id=product.id)

            product.name = name
            product.description = description
            product.price = price
            product.category = category
            product.stock_count = stock_count  

            if image1:
                product.image1 = image1
            if image2:
                product.image2 = image2
            if image3:
                product.image3 = image3

            product.save()
            messages.success(request, "Product updated successfully!")
            return redirect('admin_products')

        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
        except ValidationError as e:
            messages.error(request, f"Error: {e}")

    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin_page/edit_products.html', {
        'product': product,
        'categories': categories,
    })

 


@never_cache
@login_required(login_url='admin_login')
@admin_required
def product_stocks(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.is_in_stock:
        product.is_in_stock = False 
        messages.success(request, f"Product '{product.name}' has been unlisted (out of stock).")
    else:
        product.is_in_stock = True  
        messages.success(request, f"Product '{product.name}' has been listed (in stock).")

    product.save()

    return redirect('admin_products')







def user_product(request):
    products = Product.objects.filter(is_in_stock=True, category__is_active=True)

    show_out_of_stock = request.GET.get('show_out_of_stock', 'true')
    if show_out_of_stock == 'false':
        products = products.filter(stock_count__gt=0)

    products = products.annotate(
        final_price=Case(
            When(is_offer_applied=True, then=F('discounted_price')),
            default=F('price'),
            output_field=DecimalField()
        )
    )

    sort_by = request.GET.get('sort')
    if sort_by == 'price_low_to_high':
        products = products.order_by('final_price')  
    elif sort_by == 'price_high_to_low':
        products = products.order_by('-final_price')  
    elif sort_by == 'average_rating':
        products = products.order_by('-rating')
    elif sort_by == 'new_arrivals':
        products = products.order_by('-created_at')
    elif sort_by == 'name_a_to_z':
        products = products.order_by('name')
    elif sort_by == 'name_z_to_a':
        products = products.order_by('-name')

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user/user_product.html', {'page_obj': page_obj, 'show_out_of_stock': show_out_of_stock, 'sort_by': sort_by})





def product_detail(request, id):
    product = get_object_or_404(Product, id=id)

    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    final_price = product.discounted_price if product.is_offer_applied else product.price

    context = {
        'product': product,
        'is_in_wishlist': is_in_wishlist,
        'final_price': final_price
    }

    return render(request, 'user/user_product_details.html', context)






@never_cache
@login_required(login_url='admin_login')
@admin_required
def admin_offer(request):
    offers = Offer.objects.all().order_by('-created_at') 
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_in_stock=True)
    
    context = {
        'offers': offers,
        'categories': categories,
        'products': products
    }
    
    return render(request,'admin_page/offer_view.html',context)




@never_cache
@login_required(login_url='admin_login')
@admin_required
def add_offer(request):
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_in_stock=True, is_offer_applied=False)

    if request.method == 'POST':
        name = request.POST.get('name')
        offer_type = request.POST.get('offer_type')
        discount_percentage = request.POST.get('discount_percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = True

        try:
            if not all([name, discount_percentage, start_date, end_date, offer_type]):
                raise ValidationError('All fields are required.')

            if Offer.objects.filter(name=name).exists():
                messages.error(request, "An offer with this name already exists. Please choose a different name.")
                return redirect('admin_offer')

            discount_percentage = Decimal(discount_percentage)

            if discount_percentage <= 0 or discount_percentage > 50:
                raise ValidationError('Discount percentage must be between 1 and 50.')

            new_offer = Offer.objects.create(
                name=name,
                offer_type=offer_type,
                discount_percentage=discount_percentage,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
            )

            if offer_type == 'product':
                selected_products = request.POST.getlist('applicable_products[]')
                print("Selected Products:", selected_products)  # Debugging Line

                if not selected_products:
                    raise ValidationError('Please select at least one product for a product offer.')

                applicable_products = Product.objects.filter(id__in=selected_products, is_in_stock=True)

                for product in applicable_products:
                    discounted_price = Decimal(new_offer.apply_discount(Decimal(product.price))) 
                    product.is_offer_applied = True
                    product.discount_percentage = discount_percentage
                    product.validate_offerdate = end_date
                    product.discounted_price = discounted_price
                    product.save()

                new_offer.applicable_product.set(applicable_products) 

            elif offer_type == 'category':
                selected_categories = request.POST.getlist('applicable_categories[]')
                print("Selected Categories:", selected_categories)  # Debugging Line

                if not selected_categories:
                    raise ValidationError('Please select at least one category for a category offer.')

                applicable_categories = Category.objects.filter(id__in=selected_categories)

                for category in applicable_categories:
                    category_products = Product.objects.filter(category=category, is_in_stock=True)
                    for product in category_products:
                        discounted_price = Decimal(new_offer.apply_discount(Decimal(product.price)))  
                        product.is_offer_applied = True
                        product.discount_percentage = discount_percentage
                        product.validate_offerdate = end_date
                        product.discounted_price = discounted_price
                        product.save()

                new_offer.applicable_category.set(applicable_categories) 

            new_offer.save()
            messages.success(request, 'Offer added successfully')
            return redirect('admin_offer')

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    context = {
        'categories': categories,
        'products': products
    }

    return render(request, 'admin_page/add_offer.html', context)





@never_cache
@login_required(login_url='admin_login')
@admin_required
def edit_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_in_stock=True)

    if request.method == 'POST':
        name = request.POST.get('name')
        offer_type = request.POST.get('offer_type')
        discount_percentage = request.POST.get('discount_percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        try:
            # Remove previous offer effects
            if offer.offer_type == 'product' and offer.applicable_product.exists():
                offer.applicable_product.update(
                    is_offer_applied=False,
                    discount_percentage=None,
                    validate_offerdate=None,
                    discounted_price=None
                )
            elif offer.offer_type == 'category' and offer.applicable_category.exists():
                products = Product.objects.filter(category__in=offer.applicable_category.all())
                products.update(
                    is_offer_applied=False,
                    discount_percentage=None,
                    validate_offerdate=None,
                    discounted_price=None
                )

            discount_percentage = Decimal(discount_percentage)
            if discount_percentage <= 0 or discount_percentage > 50:
                raise ValidationError("Discount percentage must be between 1 and 50.")

            offer.name = name
            offer.offer_type = offer_type
            offer.discount_percentage = discount_percentage
            offer.start_date = start_date
            offer.end_date = end_date

            if offer_type == 'product':
                selected_products = request.POST.getlist('applicable_products[]')
                if not selected_products:
                    raise ValidationError('Please select at least one product for a product offer.')

                applicable_products = Product.objects.filter(id__in=selected_products, is_in_stock=True)

                for product in applicable_products:
                    discounted_price = product.price - (product.price * discount_percentage / Decimal(100))
                    product.is_offer_applied = True
                    product.discount_percentage = discount_percentage
                    product.validate_offerdate = end_date
                    product.discounted_price = discounted_price
                    product.save()

                offer.applicable_product.set(applicable_products)
                offer.applicable_category.clear()

            elif offer_type == 'category':
                selected_categories = request.POST.getlist('applicable_categories[]')
                if not selected_categories:
                    raise ValidationError('Please select at least one category for a category offer.')

                applicable_categories = Category.objects.filter(id__in=selected_categories)

                for category in applicable_categories:
                    category_products = Product.objects.filter(category=category, is_in_stock=True)
                    for product in category_products:
                        discounted_price = product.price - (product.price * discount_percentage / Decimal(100))
                        product.is_offer_applied = True
                        product.discount_percentage = discount_percentage
                        product.validate_offerdate = end_date
                        product.discounted_price = discounted_price
                        product.save()

                offer.applicable_category.set(applicable_categories)
                offer.applicable_product.clear()

            offer.save()
            messages.success(request, 'Offer updated successfully.')
            return redirect('admin_offer')

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    context = {
        'offer': offer,
        'categories': categories,
        'products': products
    }
    return render(request, 'admin_page/edit_offer.html', context)





@never_cache
@login_required(login_url='admin_login')
@admin_required
def delete_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)

    if offer.offer_type == 'product' and offer.applicable_product.exists():
        offer.applicable_product.update(
            is_offer_applied=False,
            discount_percentage=None,
            validate_offerdate=None,
            discounted_price=None
        )
    elif offer.offer_type == 'category' and offer.applicable_category.exists():
        products = Product.objects.filter(category__in=offer.applicable_category.all())
        products.update(
            is_offer_applied=False,
            discount_percentage=None,
            validate_offerdate=None,
            discounted_price=None
        )

    offer.delete()
    messages.success(request, 'Offer deleted successfully')
    return redirect('admin_offer')





@never_cache
@login_required(login_url='admin_login')
@admin_required
def status_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    offer.is_active = not offer.is_active  

    if not offer.is_active:
        if offer.offer_type == 'product' and offer.applicable_product.exists():
            offer.applicable_product.update(
                is_offer_applied=False,
                discount_percentage=None,
                validate_offerdate=None,
                discounted_price=None
            )
        elif offer.offer_type == 'category' and offer.applicable_category.exists():
            products = Product.objects.filter(category__in=offer.applicable_category.all())
            products.update(
                is_offer_applied=False,
                discount_percentage=None,
                validate_offerdate=None,
                discounted_price=None
            )

    offer.save()
    messages.success(request, 'Offer status updated successfully')
    return redirect('admin_offer')
