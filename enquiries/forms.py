import time

from django import forms
from django.conf import settings
from django.core import signing
from django.core.validators import MaxLengthValidator
from .models import Enquiry
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

MESSAGE_MAX_LENGTH = 5000
# A form left open longer than this must be sent again (stops one old page being reused by bots)
FORM_MAX_AGE_SECONDS = 24 * 60 * 60


def single_line(value):
    """Collapse line breaks, tabs and other control characters into single spaces.

    Names end up in email subjects, where a line break could add extra email headers.
    """
    return ' '.join(''.join(ch if ch.isprintable() else ' ' for ch in value or '').split())

class EnquiryForm(forms.ModelForm):
    # Submissions sent sooner than this after the page loaded are treated as bots
    MIN_SECONDS_TO_SUBMIT = 3

    # Spam trap: a normal text box moved off-screen by CSS (#div_id_website), so people
    # never see it but form-filling bots do. Anything typed here marks the enquiry as spam.
    website = forms.CharField(
        required=False,
        # No visible label and hidden from screen readers (21 Nov 2026): people never meet it, bots still fill it
        label='',
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off', 'aria-hidden': 'true'}),
    )
    # Signed time the form was shown, to catch instant bot submissions
    form_started = forms.CharField(required=False, widget=forms.HiddenInput())

    consent_given = forms.BooleanField(
        required=True,
        label="I consent to Desi Roots storing my details and contacting me regarding this enquiry.",
        error_messages={'required': 'You must agree to the privacy policy to submit an enquiry.'}
    )

    class Meta:
        model = Enquiry
        fields = [
            'name', 
            'business_name', 
            'email', 
            'phone', 
            'message', 
            'consent_given'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your Full Name'}),
            'business_name': forms.TextInput(attrs={'placeholder': 'e.g., Bristol Spice Kitchen Ltd'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g., info@yourbusiness.co.uk'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g., 0117 900 0000'}),
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about the products, quantities, or delivery schedule you require...'}),
        }
        labels = {
            'name': 'Full Name',
            'business_name': 'Business Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'message': 'Enquiry / Message Details',
            'consent_given': 'Privacy Consent',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['message'].required = True
        self.fields['consent_given'].required = True
        # Keep messages to a sensible size (no database change needed)
        self.fields['message'].validators.append(MaxLengthValidator(MESSAGE_MAX_LENGTH))
        self.fields['message'].widget.attrs['maxlength'] = MESSAGE_MAX_LENGTH
        if not self.is_bound:
            self.fields['form_started'].initial = signing.dumps(int(time.time()), salt='enquiry-form')
        # Set by clean(); the view quietly drops spam instead of telling the bot why
        self.is_spam = False

    def clean_name(self):
        return single_line(self.cleaned_data.get('name'))

    def clean_business_name(self):
        return single_line(self.cleaned_data.get('business_name'))

    def clean_phone(self):
        return single_line(self.cleaned_data.get('phone'))

    def looks_like_spam(self, cleaned_data):
        if cleaned_data.get('website'):
            return True
        try:
            started = signing.loads(cleaned_data.get('form_started') or '', salt='enquiry-form')
        except signing.BadSignature:
            return True  # missing or forged: posted without loading the page
        age = time.time() - started
        if age > FORM_MAX_AGE_SECONDS:
            # A real person may leave the page open overnight: ask them to send again with a fresh form
            self.data = self.data.copy()
            self.data['form_started'] = signing.dumps(int(time.time()), salt='enquiry-form')
            raise forms.ValidationError("This form was open for a long time. Please check your details and press Send again.")
        return age < self.MIN_SECONDS_TO_SUBMIT


    def clean(self):
        cleaned_data = super().clean()
        
        # 1. Spam trap and timing check
        if self.looks_like_spam(cleaned_data):
            self.is_spam = True
            return cleaned_data

        # 2. Cloudflare Turnstile check (only when both keys are set; the contact page shows the widget then)
        if self.request and settings.TURNSTILE_SECRET_KEY and settings.TURNSTILE_SITE_KEY:
            turnstile_response = self.request.POST.get('cf-turnstile-response')
            if not turnstile_response:
                raise forms.ValidationError("Spam verification token is missing. Please refresh the page.")

            # Make POST request to Cloudflare verify URL
            verify_url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
            post_data = urllib.parse.urlencode({
                'secret': settings.TURNSTILE_SECRET_KEY,
                'response': turnstile_response,
                'remoteip': self.get_client_ip()
            }).encode('utf-8')

            try:
                req = urllib.request.Request(verify_url, data=post_data, method='POST')
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
            except (urllib.error.URLError, TimeoutError, ValueError):
                # Cloudflare unreachable: let the enquiry through rather than lose a customer
                logger.warning("Turnstile verification could not be reached; enquiry allowed")
                return cleaned_data
            if not res_data.get('success'):
                raise forms.ValidationError("Spam verification failed. Please try again.")

        return cleaned_data

    def get_client_ip(self):
        if not self.request:
            return ''
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
