from django import forms
from django.conf import settings
from .models import Enquiry
import urllib.request
import urllib.parse
import json

class EnquiryForm(forms.ModelForm):
    # Spam prevention honeypot field (hidden from users via CSS)
    website = forms.CharField(
        required=False, 
        widget=forms.HiddenInput(),
        label="Leave this field blank"
    )

    consent_given = forms.BooleanField(
        required=True,
        label="I consent to Spice Pantry storing my details and contacting me regarding this enquiry.",
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


    def clean(self):
        cleaned_data = super().clean()
        
        # 1. Check Honeypot field
        website = cleaned_data.get('website')
        if website:
            raise forms.ValidationError("Spam detected.")

        # 2. Check Turnstile Verification
        if self.request and settings.TURNSTILE_SECRET_KEY:
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
                    if not res_data.get('success'):
                        raise forms.ValidationError("Spam verification failed. Please try again.")
            except Exception as e:
                # Log or handle connection issues - but don't block user if cloudflare is down
                pass

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
