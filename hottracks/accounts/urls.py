
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include

urlpatterns = [
    path('', views.user_home, name='user_home'),
    
    # User Login
    path('user_login/',views.user_login,name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('user_signup/',views.user_signup,name='user_signup'),
    path('user_shop/',views.user_shop,name='user_shop'),
    path('user_otp/', views.user_otp, name='user_otp'),
    path('resend_otp/', views.user_resend_otp, name='user_resend_otp'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('resend-reset-otp/', views.resend_reset_otp, name='resend_reset_otp'),
    
    # User profile
    path('view_address/', views.view_address, name='view_address'),
    path('add_address/', views.add_address, name='add_address'),
    path('delete_address/<int:add_id>/', views.delete_address, name='delete_address'),
    path('edit_address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('change_password/', views.change_password, name='change_password'),
    

    
    # admin_side 
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_user/', views.admin_user, name='admin_user'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    
    
    path('accounts/', include('allauth.urls')),
 

    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
