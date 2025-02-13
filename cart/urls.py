from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # cart
    path('user_cart/', views.user_cart, name='user_cart'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update_item/', views.update_cart_item, name='update_cart_item'),
    path('delete_from_cart/<int:product_id>/', views.delete_from_cart, name='delete_from_cart'),
    path('cart/order/<int:order_id>/details/', views.order_details_view, name='order_details'),  # Fix this
    path('wishlist/<int:product_id>/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/', views.wishlist, name='wishlist'),

    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist-to-cart/<int:product_id>/', views.wishlist_to_cart, name='wishlist_to_cart'),
    path('get-wishlist-count/', views.get_wishlist_count, name='get_wishlist_count'),
    path('order/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('wallet_view/',views.wallet_view,name='wallet_view'),
    # payment
    path('user_account/', views.user_account, name='user_account'),
    
    # admin side order management
    path('admin/order-management/', views.admin_user_order_management, name='admin_user_order_management'),
    path('admin/order-management/update/<int:order_id>/', views.update_order, name='update_order'),]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
