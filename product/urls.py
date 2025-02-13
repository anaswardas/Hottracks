from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Urls Products
    path('admin_products/', views.product_view, name='admin_products'),
    path('add/', views.add_product, name='add_product'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),  
    path('stocks/<int:product_id>/', views.product_stocks, name='product_stocks'),
    path('user_product/', views.user_product, name='user_product'),
    path('product/<int:id>/', views.product_detail, name='user_product_detail'),
    
    # Urls Category
    path('admin_category/', views.category_view, name='admin_category'),
    path('add_category/', views.add_category, name='add_category'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),  
    path('status/<int:category_id>/', views.category_status, name='category_status'),
    
    
    # Offer
    path('admin_offer/', views.admin_offer, name='admin_offer'),
    path('admin/offers/add/', views.add_offer, name='add_offer'),
    path('admin/offers/edit/<int:offer_id>/', views.edit_offer, name='edit_offer'),
    path('admin/offers/delete/<int:offer_id>/', views.delete_offer, name='delete_offer'),
    path('admin/offers/status/<int:offer_id>/', views.status_offer, name='status_offer'),

    
]

# Add static and media URL settings
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
