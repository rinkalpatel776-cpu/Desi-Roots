"""Admin sign-in security: wrong passwords, lockout, and who may open admin pages.

Added 2026-11-18 after the "all tests pass, but a wrong password still logged in" warning:
these tests prove the login really refuses bad passwords, so a future change can't quietly break it.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from enquiries.models import Enquiry

PASSWORD = 'Correct-Horse-Battery-9'


class AdminLoginTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser('owner', 'owner@example.test', PASSWORD)
        self.login_url = reverse('admin:login')
        self.index_url = reverse('admin:index')

    def login(self, password, username='owner'):
        return self.client.post(self.login_url, {'username': username, 'password': password,
                                                 'next': self.index_url})

    def is_signed_in(self):
        return '_auth_user_id' in self.client.session

    def test_admin_is_not_at_the_default_address(self):
        self.assertNotEqual(self.index_url, '/admin/')
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    def test_wrong_password_is_refused(self):
        for bad in ('wrong', '', PASSWORD.lower(), PASSWORD + ' ', 'Correct-Horse-Battery-'):
            response = self.login(bad)
            self.assertEqual(response.status_code, 200, repr(bad))  # the form is shown again
            self.assertFalse(self.is_signed_in(), f'signed in with {bad!r}')
            message = 'This field is required' if bad == '' else 'Please enter the correct username and password'
            self.assertContains(response, message)
        self.assertEqual(self.client.get(self.index_url).status_code, 302)  # still sent to the login page

    def test_unknown_user_is_refused(self):
        self.login(PASSWORD, username='nobody')
        self.assertFalse(self.is_signed_in())

    def test_correct_password_signs_in(self):
        response = self.login(PASSWORD)
        self.assertRedirects(response, self.index_url)
        self.assertTrue(self.is_signed_in())

    def test_non_staff_user_cannot_use_admin(self):
        get_user_model().objects.create_user('customer', 'c@example.test', PASSWORD)
        self.login(PASSWORD, username='customer')
        self.assertFalse(self.is_signed_in())
        self.client.force_login(get_user_model().objects.get(username='customer'))
        response = self.client.get(reverse('admin:enquiries_enquiry_changelist'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response['Location'])


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=5)
class AdminLockoutTests(TestCase):
    """Development settings switch django-axes off, so these tests switch it back on as on the live site."""

    def setUp(self):
        get_user_model().objects.create_superuser('owner', 'owner@example.test', PASSWORD)
        self.login_url = reverse('admin:login')

    def login(self, password):
        return self.client.post(self.login_url, {'username': 'owner', 'password': password})

    def test_five_wrong_passwords_lock_the_login_even_for_the_right_password(self):
        for _ in range(4):
            self.assertEqual(self.login('wrong').status_code, 200)
        locked = self.login('wrong')                    # 5th failure locks
        self.assertEqual(locked.status_code, 429)
        self.assertContains(locked, 'Too many sign-in attempts', status_code=429)
        after = self.login(PASSWORD)                    # the real password no longer works either
        self.assertEqual(after.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_a_few_mistakes_then_the_right_password_still_works(self):
        for _ in range(3):
            self.login('wrong')
        self.assertEqual(self.login(PASSWORD).status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)


class AdminPagesNeedSignInTests(TestCase):
    """A visitor who is not signed in must never see customer enquiries or any admin page."""

    def setUp(self):
        self.enquiry = Enquiry.objects.create(name='Private Person', email='private@example.test',
                                              phone='07000000000', message='Secret order details')

    def test_every_admin_page_sends_visitors_to_the_login(self):
        login_url = reverse('admin:login')
        urls = [
            reverse('admin:index'),
            reverse('admin:enquiries_enquiry_changelist'),
            reverse('admin:enquiries_enquiry_change', args=[self.enquiry.pk]),
            reverse('admin:enquiries_enquiry_delete', args=[self.enquiry.pk]),
            reverse('admin:catalogue_product_changelist'),
            reverse('admin:catalogue_product_add'),
            reverse('admin:auth_user_changelist'),
            reverse('admin:core_sitesettings_changelist'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertTrue(response['Location'].startswith(login_url), url)
            self.assertNotContains(response, 'Private Person', status_code=302)

    def test_posting_to_admin_without_sign_in_changes_nothing(self):
        url = reverse('admin:enquiries_enquiry_delete', args=[self.enquiry.pk])
        self.client.post(url, {'post': 'yes'})
        self.assertTrue(Enquiry.objects.filter(pk=self.enquiry.pk).exists())
