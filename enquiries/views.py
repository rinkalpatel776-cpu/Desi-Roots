from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .forms import EnquiryForm
from .models import Enquiry
from catalogue.models import Product
import urllib.request
import urllib.parse
import json

def wholesale_enquiry(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST, request=request)
        if form.is_valid():
            enquiry = form.save()
            
            # Send Notification Emails (with error tolerance)
            try:
                # 1. Email to Admin
                admin_subject = f"New Website Enquiry from {enquiry.name}"
                admin_message = (
                    f"You have received a new website enquiry.\n\n"
                    f"Name: {enquiry.name}\n"
                    f"Phone No: {enquiry.phone}\n"
                    f"Email: {enquiry.email}\n\n"
                    f"Message:\n{enquiry.message}\n"
                )
                send_mail(
                    subject=admin_subject,
                    message=admin_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.NOTIFICATION_EMAIL],
                    fail_silently=False
                )

                # 2. Email to Customer (Auto-responder)
                customer_subject = "Enquiry Received - Spice Pantry"
                customer_message = (
                    f"Dear {enquiry.name},\n\n"
                    f"Thank you for contacting Spice Pantry. We have received your enquiry.\n\n"
                    f"Our team is currently reviewing your message and a manager will contact you within 24 business hours.\n\n"
                    f"Best regards,\n"
                    f"The Spice Pantry Team\n"
                    f"Desi Roots Wholesale Supply\n"
                )
                send_mail(
                    subject=customer_subject,
                    message=customer_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[enquiry.email],
                    fail_silently=False
                )
            except Exception as e:
                # Log email errors silently so that database save is not rolled back 
                # and visitor still reaches the thank-you page
                pass

            return redirect('/wholesale/thank-you/')
    else:
        # Pre-populate message if product_id is in query parameters
        initial_data = {}
        product_id = request.GET.get('product_id')
        if product_id:
            try:
                product = Product.objects.get(id=product_id, is_published=True)
                initial_data['message'] = f"Hello, I am interested in wholesale pricing and availability for {product.name}."
            except (Product.DoesNotExist, ValueError):
                pass
                
        form = EnquiryForm(initial=initial_data)

    context = {
        'form': form,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
    }
    return render(request, 'enquiries/wholesale_form.html', context)


def thank_you(request):
    return render(request, 'enquiries/thank_you.html')


