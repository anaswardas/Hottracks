
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required, user_passes_test
from product.models import Product,Category
import re
from django.shortcuts import render, redirect, get_object_or_404
from .models import Users,Address
from django.http import JsonResponse
import random
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.views.decorators.cache import cache_control
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from datetime import datetime
from allauth.socialaccount.models import SocialAccount

# Create your views here.




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_home(request):
    products = Product.objects.all()[:4]  
    categories = Category.objects.all()[:4]  
    context = {
        'products': products,
        'categories': categories,  
        'user': request.user,
    }
    return render(request, 'user/user_home.html', context)





@login_required
def user_profile(request):
    try:
        google_account = SocialAccount.objects.get(user=request.user, provider='google')
        # Access Google account info if needed
        google_data = google_account.extra_data
    except SocialAccount.DoesNotExist:
        google_data = None
    
    return render(request, 'user/profile.html', {'google_data': google_data})


# User login
@cache_control(no_cash=True,must_revalidate=True, no_store=True)
def user_login(request):
    if request.user.is_authenticated:
        return redirect('user_home')  

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user_exists = Users.objects.filter(username=username).exists()
        if not user_exists:
            messages.error(request, "Invalid username or password. Please try again.", extra_tags='login_error')
            return redirect('user_login')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active:
            auth_login(request, user)
            messages.success(request, "You have successfully logged in!")
            return redirect('user_home')  
        else:
            messages.error(request, "Invalid username or password. Please try again.", extra_tags='login_error')
            return redirect('user_login')

    response = render(request, 'user/user_login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response





@cache_control(no_cash=True,must_revalidate=True, no_store=True)
def user_logout(request):
    auth_logout(request)
    request.session.flush()
    messages.success(request, "You have successfully logged out!",extra_tags='logout_message')
    return redirect('user_login')





def user_signup(request):
    if request.user.is_authenticated:
        return redirect('user_home')

   
    if request.session.get('temp_user_data'):
        return redirect('user_otp')

    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

       
        try:
            RegexValidator(r'^[a-zA-Z0-9]+$', 'Username must contain only letters and numbers.')(username)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('user_signup')

        
        if Users.objects.filter(username__iexact=username).exists():
            messages.error(request, "This username is already taken. Please choose another.")
            return redirect('user_signup')
        
        if Users.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered. Please use another.")
            return redirect('user_signup')

        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')

        otp = random.randint(1000, 9999)
        print(otp, "OTP generated")

       
        request.session['temp_user_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'otp': otp
        }
        request.session.modified = True 
        # Send OTP email
        try:
            send_mail(
                'Your OTP Verification Code',
                f'Your OTP is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            print("OTP sent successfully")
        except Exception as e:
            print(f"Error sending OTP: {e}")
            messages.error(request, "There was an issue sending the OTP. Please try again later.")
            return redirect('user_signup')

        messages.success(request, "An OTP has been sent to your email. Please verify.")
        return redirect('user_otp')

    return render(request, 'user/user_signup.html')




def user_otp(request):
    session_data = request.session.get('temp_user_data', {})

    print("Session Data at user_otp:", session_data)

    if not session_data:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('user_signup')

    if request.method == 'POST':
        user_otp = request.POST.get('otp')

        if str(user_otp) == str(session_data.get('otp')):
            username = session_data.get('username')  # This might be None
            email = session_data.get('email')
            password = session_data.get('password')

            if not username:  # Check if username is missing
                messages.error(request, "Session data missing. Please sign up again.")
                return redirect('user_signup')

            user = Users.objects.create_user(username=username, email=email, password=password)
            user.save()

            # Explicitly delete session data
            if 'temp_user_data' in request.session:
                del request.session['temp_user_data']
                request.session.modified = True

            messages.success(request, "Your account has been created successfully!")
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('user_otp')

    return render(request, 'user/user_otp.html')





def user_resend_otp(request):
    session_data = request.session.get('temp_user_data', {})
    if not session_data:
        return JsonResponse({"success": False, "message": "Session expired. Please sign up again."}, status=400)

    try:
        new_otp = random.randint(1000, 9999)
        session_data['otp'] = new_otp

        request.session['temp_user_data'] = session_data
        request.session.modified = True 
        print(f"Resent OTP: {new_otp}")  

        send_mail(
            'Your OTP Verification Code',
            f'Your new OTP is: {new_otp}',
            settings.EMAIL_HOST_USER,
            [session_data['email']],
            fail_silently=False,
        )
        return JsonResponse({"success": True, "message": "A new OTP has been sent to your email."})
    except Exception as e:
        return JsonResponse({"success": False, "message": "Failed to resend OTP. Please try again later."}, status=500)






def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            messages.error(request, "Email is incorrect. Please enter a valid email.")
            return redirect('forgot_password')
        
        otp = random.randint(1000, 9999)
        print(otp, 'Generated OTP')
        
        request.session['password_reset_data'] = {
            'email': email,
            'otp': otp,
            'otp_created_at': str(timezone.now()),
            'is_password_reset': True  # Flag to identify password reset flow
        }
        request.session.modified = True
        
        try:
            send_mail(
                'Your Password Reset OTP',
                f'Your OTP for password reset is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            print('OTP Sent successfully')
        except Exception as e:
            print(f'Error sending OTP: {e}')
            messages.error(request, "There was an issue sending the OTP. Please try again later.")
            return redirect('forgot_password')
            
        messages.success(request, "An OTP has been sent to your email. Please verify.")
        return redirect('verify_reset_otp')
    
    return render(request, 'user/forgot_password.html')


def resend_reset_otp(request):
    session_data = request.session.get('password_reset_data')

    if not session_data or not session_data.get('is_password_reset'):
        print("Session expired or invalid")  # Debugging line
        return JsonResponse({
            "success": False,
            "message": "Password reset session expired. Please try again."
        }, status=400)

    email = session_data.get('email')
    if not email:
        print("Email not found in session")  # Debugging line
        return JsonResponse({
            "success": False,
            "message": "Invalid session data."
        }, status=400)

    try:
        new_otp = random.randint(1000, 9999)
        session_data['otp'] = new_otp
        session_data['otp_created_at'] = str(timezone.now())
        request.session['password_reset_data'] = session_data
        request.session.modified = True

        print(f"New OTP: {new_otp}")  # Debugging line

        send_mail(
            'Your Password Reset OTP',
            f'Your new OTP is: {new_otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return JsonResponse({
            "success": True,
            "message": "A new OTP has been sent to your email."
        })

    except Exception as e:
        print(f"Error sending OTP: {e}")  # Debugging line
        return JsonResponse({
            "success": False,
            "message": "Failed to resend OTP. Please try again later."
        }, status=500)
       
        

def verify_reset_otp(request):
    session_data = request.session.get('password_reset_data')
    
    if not session_data or not session_data.get('is_password_reset'):
        messages.error(request, "Password reset session expired. Please try again.")
        return redirect('forgot_password')

    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        
        if str(user_otp) == str(session_data.get('otp')):
            request.session['reset_email'] = session_data['email']
            
            del request.session['password_reset_data']
            request.session.modified = True
            
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_reset_otp')
    
    otp_created_at = datetime.fromisoformat(session_data.get('otp_created_at'))
    current_time = timezone.now()
    time_elapsed = (current_time - otp_created_at).total_seconds()
    time_remaining = max(0, 60 - int(time_elapsed))  # 300 seconds = 5 minutes
    
    context = {
        'time_remaining': time_remaining
    }
    
    return render(request, 'user/verify_reset_otp.html', context)


def reset_password(request):
    reset_email = request.session.get('reset_email')
    
    if not reset_email:
        messages.error(request, "Password reset session expired. Please start over.")
        return redirect('forgot_password')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')
        
        password_regex = r'^(?=.*[A-Z])(?=.*\W)(?!.*\s).{8,}$'
        if not re.match(password_regex, new_password):
            messages.error(request, 'Password must be 8-20 characters long, contain at least one capital letter, one special character, and must not contain spaces.')
            return redirect('reset_password')
        
        try:
            user = Users.objects.get(email=reset_email)
            user.set_password(new_password)
            user.save()
            
            if 'reset_email' in request.session:
                del request.session['reset_email']
            request.session.modified = True
            
            messages.success(request, "Password has been reset successfully. Please login with your new password.")
            return redirect('user_login')
            
        except Users.DoesNotExist:
            messages.error(request, "User not found. Please try again.")
            return redirect('forgot_password')
    
    return render(request, 'user/reset_password.html')



def user_shop(request):
    return render (request,'user/user_shop.html')




@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('loginUsername')
        password = request.POST.get('loginPassword')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('dashboard') 
            else:
                messages.error(request, 'Access restricted to superusers only.')
        else:
            messages.error(request, 'Invalid username or password.')

   
    csrf_token = get_token(request)

    return render(request, 'admin_page/admin_login.html', {'csrf_token': csrf_token})




@never_cache
def admin_logout(request):
   
    logout(request)

    
    response = redirect('admin_login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)


@never_cache
@login_required(login_url='admin_login')
@admin_required
def dashboard(req):
    return render(req,'admin_page/dashboard.html')




@never_cache
@login_required(login_url='admin_login')
@admin_required
def admin_user(request):
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        try:
            user = Users.objects.get(id=user_id)

            
            if user.is_superuser:
                messages.error(request, "You cannot block or unblock admin users.")
                return redirect('admin_user')

            if action == "block":
                user.is_active = False
                user.save()
                messages.success(request, f"User {user.username} has been blocked.")
            elif action == "unblock":
                user.is_active = True
                user.save()
                messages.success(request, f"User {user.username} has been unblocked.")
        except Users.DoesNotExist:
            messages.error(request, "User not found.")

   
    users = Users.objects.exclude(is_superuser=True)

    return render(request, 'admin_page/admin_user.html', {'users': users})





indian_states = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh",
    "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry",
    "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
]



@never_cache
@login_required(login_url='user_login')
def add_address(request):
    if request.method == 'POST':
        user = request.user
        name = request.POST.get('firstname', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        house_no = request.POST.get('house_no', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        country = request.POST.get('country', '').strip()
        pincode = request.POST.get('pincode', '').strip()

        if not all([name, phone, email, house_no, city, state, country, pincode]):
            messages.error(request, "Please provide all fields.")
            return redirect('view_address')

        if state.casefold() not in [state_name.casefold() for state_name in indian_states]:
            messages.error(request, "Please provide a valid state.")
            return redirect('view_address')

        if not re.match(r'^[1-9][0-9]{5}$', pincode):
            messages.error(request, "Invalid pincode format. Please enter a valid Indian pincode.")
            return redirect('view_address')

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            messages.error(request, "Invalid email format.")
            return redirect('view_address')

        if not re.match(r'^\d{10}$', phone):
            messages.error(request, "Invalid phone number. Please enter a 10-digit phone number.")
            return redirect('view_address')

        Address.objects.create(
            user=user,
            name=name,
            phone=phone,
            email=email,
            house_no=house_no,
            city=city,
            state=state,
            country=country,
            pincode=pincode,
        )
        messages.success(request, "Address added successfully.")
        return redirect('view_address')

    return render(request, 'user/user_address.html')

@never_cache
@login_required(login_url='user_login')
def view_address(request):
    user = request.user
    address = Address.objects.filter(user=user, is_delete=False)

    context = {
        'user': user,
        'Addresses': address,
    }
    return render(request, 'user/user_address.html', context)





@never_cache
@login_required(login_url='user_login')
def delete_address(request, add_id):
    user = request.user
    address = get_object_or_404(Address, pk=add_id, user=user)
    address.is_delete = not address.is_delete
    address.save()
    messages.success(request, 'Address deleted successfully')
    return redirect('view_address')




@never_cache
@login_required(login_url="login")
def edit_address(request, address_id):
    address = get_object_or_404(Address, pk=address_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        house_no = request.POST.get("house_no", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        country = request.POST.get("country", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        phone = request.POST.get("phone", "").strip()

        errors = []
        if not name or len(name) < 3:
            errors.append("Name is required.")
        if not house_no:
            errors.append("House No. is required.")
        if not city or len(city) < 3:
            errors.append("City is required.")
        if not state or len(state) < 3:
            errors.append("State is required.")
        if not country or len(country) < 3:
            errors.append("Country is required.")
        if not pincode:
            errors.append("Pincode is required.")
        if not phone:
            errors.append("Phone is required.")
        elif not phone.isdigit():
            errors.append("Phone number should only contain digits.")
        elif len(phone) < 10:
            errors.append("Phone number should be at least 10 digits long.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('view_address')

        if state.casefold() not in [state_name.casefold() for state_name in indian_states]:
            messages.error(request, "Please provide a valid state.")
            return redirect('view_address')

        if not re.match(r'^[1-9][0-9]{5}$', pincode):
            messages.error(request, "Invalid pincode format. Please enter a valid Indian pincode.")
            return redirect('view_address')

        if not re.match(r'^\d{10}$', phone):
            messages.error(request, "Invalid phone number. Please enter a 10-digit phone number.")
            return redirect('view_address')

        address.name = name
        address.house_no = house_no
        address.city = city
        address.state = state
        address.country = country
        address.pincode = pincode
        address.phone = phone

        address.save()

        messages.success(request, 'Address updated successfully')
        return redirect('view_address')

    context = {
        'address': address
    }
    return render(request, 'user/user_address.html', context)






@never_cache
@login_required(login_url="login")
def change_password(request):
    user = request.user
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
       
        password_regex = r'^(?=.*[A-Z])(?=.*\W)(?!.*\s).{8,}$'
        
        if new_password1 != new_password2:
            messages.error(request, 'New Passwords do not match')
            return redirect('change_password')
        
        if not re.match(password_regex, new_password1):
            messages.error(request, 'Password must be 8-20 characters long, contain at least one capital letter, one special character, and must not contain spaces.')
            return redirect('change_password')
        
        user = authenticate(request, username=request.user.username, password=old_password)
        if user is not None:
            user.set_password(new_password1)
            user.save()

            auth_logout(request)
            request.session.flush()

            messages.success(request, 'Password changed successfully. Please log in again.')
            return redirect('user_login')  
        else:
            messages.error(request, 'Old Password is incorrect')
            return redirect('change_password')
        
    return render(request, 'user/change_password.html')
