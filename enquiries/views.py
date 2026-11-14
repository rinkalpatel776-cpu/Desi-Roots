from django.shortcuts import render, redirect
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
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
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Auto-reply emails per visitor address per hour. Stops anyone using the form to make
# our mailbox send emails to strangers (which could get support@desiroots.co.uk blocked).
AUTO_REPLY_LIMIT_PER_HOUR = 3


def _auto_reply_allowed(request):
    ip = request.META.get('REMOTE_ADDR', '')
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        ip = forwarded.split(',')[-1].strip()  # the address Nginx saw
    key = f'enquiry-auto-reply:{ip}'
    count = cache.get(key, 0)
    if count >= AUTO_REPLY_LIMIT_PER_HOUR:
        return False
    cache.set(key, count + 1, 3600)
    return True

def handle_enquiry_form(request, template_name):
    """Shows the enquiry form, saves valid submissions and sends the notification emails."""
    if request.method == 'POST':
        form = EnquiryForm(request.POST, request=request)
        if form.is_valid() and form.is_spam:
            # Bots get the normal thank-you page, but nothing is saved or emailed
            return redirect('/wholesale/thank-you/')
        if form.is_valid():
            enquiry = form.save()
            
            # Send Notification Emails (with error tolerance)
            try:
                # 1. Email to Admin
                admin_subject = f"New Website Enquiry: {enquiry.business_name or enquiry.name}"
                admin_message = (
                    f"You have received a new wholesale website enquiry.\n\n"
                    f"Full Name: {enquiry.name}\n"
                    f"Business Name: {enquiry.business_name or 'N/A'}\n"
                    f"Phone Number: {enquiry.phone}\n"
                    f"Email Address: {enquiry.email}\n\n"
                    f"Message:\n{enquiry.message}\n"
                )
                send_mail(
                    subject=admin_subject,
                    message=admin_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.NOTIFICATION_EMAIL],
                    fail_silently=False
                )

                # 2. Email to Customer (Auto-responder), limited per visitor
                if not _auto_reply_allowed(request):
                    logger.warning("Enquiry %s saved; auto-reply skipped (hourly limit)", enquiry.pk)
                    return redirect('/wholesale/thank-you/')
                customer_subject = "Enquiry Received - Desi Roots"
                customer_message = (
                    f"Dear {enquiry.name},\n\n"
                    f"Thank you for contacting Desi Roots. We have received your wholesale enquiry.\n\n"
                    f"We'll look at the products and quantities you asked for and get back to you with a price quote.\n\n"
                    f"Best regards,\n"
                    f"The Desi Roots Team\n"
                    f"desiroots.co.uk\n"
                )
                send_mail(
                    subject=customer_subject,
                    message=customer_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[enquiry.email],
                    fail_silently=False
                )
            except Exception:
                # The enquiry is already saved in the admin; record the email problem so staff can see it
                logger.exception("Enquiry %s saved but an email could not be sent", enquiry.pk)

            return redirect('/wholesale/thank-you/')
    else:
        # Pre-fill the message when arriving from a product page (?product_id=)
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
    return render(request, template_name, context)


def wholesale_enquiry(request):
    """
    Old enquiry URL. Enquiries now live on the contact page, so visits redirect
    there permanently (keeping ?product_id=), and posts from a page that was
    open before the change are still accepted.
    """
    if request.method == 'POST':
        return handle_enquiry_form(request, 'pages/contact.html')
    url = reverse('pages:contact')
    query = request.META.get('QUERY_STRING', '')
    return HttpResponsePermanentRedirect(f"{url}?{query}" if query else url)


def thank_you(request):
    return render(request, 'enquiries/thank_you.html')


