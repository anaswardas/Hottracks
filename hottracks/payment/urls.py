from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('checkout_view/', views.checkout_view, name='checkout_view'),
    path('checkout_success/', views.checkout_success, name='checkout_success'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('admin_coupon/',views.admin_coupon_view,name='admin_coupon'),
    path('add_coupon',views.add_coupon,name='add_coupon'),
    path('edit_coupon/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('coupon/status/<int:coupon_id>/', views.coupon_status, name='coupon_status'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    path('admin/sales-report/', views.sales_report, name='admin_sales_report'),
    

        
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
