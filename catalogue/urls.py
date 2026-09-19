from django.urls import path
from . import views

app_name = 'catalogue'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('categories/<slug:slug>/', views.category_detail_redirect, name='category_detail'),
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/<slug:slug>/', views.brand_detail_redirect, name='brand_detail'),
]
