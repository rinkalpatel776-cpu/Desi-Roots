from django.urls import path
from . import views

app_name = 'enquiries'

urlpatterns = [
    path('wholesale/', views.wholesale_enquiry, name='wholesale_enquiry'),
    path('wholesale/thank-you/', views.thank_you, name='thank_you'),
]
