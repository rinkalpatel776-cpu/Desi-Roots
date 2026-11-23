"""Browser (end-to-end) tests: a real Chromium clicks through the site.

Run on a development machine only:
    E2E=1 python manage.py test e2e --settings=config.settings.dev
Without E2E=1, or where Playwright is not installed (the live server), these tests are skipped.
"""
import os
import re
import time
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import override_settings, tag

from catalogue.models import Brand, Category, PackSize, Product
from enquiries.models import Enquiry

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:  # not installed on the live server
    sync_playwright = None

RUN = os.environ.get('E2E') == '1' and sync_playwright is not None
PHONE = {'width': 375, 'height': 812}
DESKTOP = {'width': 1280, 'height': 900}
# Tests that are not about the privacy pop-up start with it answered ("Reject All")
HIDE_COOKIE_POP_UP = "try { localStorage.setItem('dr_cookie_consent', 'denied') } catch (e) {}"
GA = 'G-TEST12345'


@tag('e2e')
@unittest.skipUnless(RUN, 'Browser tests run only with E2E=1 and Playwright installed')
@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='', NOTIFICATION_EMAIL='support@example.com')
class BrowserJourneyTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # Playwright runs its own event loop; let the test thread use the database alongside it
        os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
        super().setUpClass()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        super().tearDownClass()

    def setUp(self):
        # Each test starts with an empty cache, so enquiry limits from earlier runs can't block it
        from django.core.cache import cache
        cache.clear()
        spices = Category.objects.create(name='Spices & Masalas', slug='spices-masalas', display_order=1, show_on_home=True)
        rice = Category.objects.create(name='Rice', slug='rice', display_order=2, show_on_home=True)
        heera = Brand.objects.create(name='Heera', slug='heera', is_featured=True, home_order=1)
        for i in range(8):
            Brand.objects.create(name=f'Brand {i}', slug=f'brand-{i}', is_featured=True, home_order=i + 2)
        self.chilli = Product.objects.create(name='Heera Chilli Powder', slug='heera-chilli-powder', category=spices,
                                             brand=heera, is_published=True)
        PackSize.objects.create(product=self.chilli, size='10 x 400 g')
        Product.objects.create(name='Heera Basmati Rice', slug='heera-basmati-rice', category=rice, brand=heera,
                               is_published=True)
        Product.objects.create(name='Hidden Draft Rice', slug='hidden-draft', category=rice, brand=heera,
                               is_published=False)

    def page(self, viewport=DESKTOP):
        context = self.browser.new_context(viewport=viewport)
        context.add_init_script(HIDE_COOKIE_POP_UP)
        self.addCleanup(context.close)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        self.addCleanup(lambda: self.assertEqual(errors, [], 'JavaScript errors on the page'))
        return page

    def no_sideways_scroll(self, page):
        width = page.evaluate('document.documentElement.scrollWidth')
        self.assertLessEqual(width, page.viewport_size['width'], f'{page.url} scrolls sideways')

    def test_every_main_page_loads_with_one_h1_on_phone_and_desktop(self):
        for viewport in (DESKTOP, PHONE):
            page = self.page(viewport)
            for path in ('/', '/products/', '/brands/', '/about/', '/faq/', '/contact/',
                         '/privacy/', '/cookies/', '/terms/'):
                response = page.goto(self.live_server_url + path)
                self.assertEqual(response.status, 200, path)
                self.assertEqual(page.locator('h1').count(), 1, f'{path} at {viewport}')
                self.no_sideways_scroll(page)

    def test_hero_slider_keeps_moving_after_clicks_and_hover(self):
        page = self.page()
        page.goto(self.live_server_url + '/')
        current = lambda: page.evaluate(
            "[...document.querySelectorAll('.hs-dot')].findIndex(d => d.getAttribute('aria-current') === 'true')")
        self.assertEqual(current(), 0)
        self.assertEqual(page.locator('.hs-pause').count(), 0)  # no pause button (owner's request)
        expect(page.locator('.hs-slide').nth(1)).to_have_attribute('aria-hidden', 'true')
        # Mouse resting on the slider does not stop it
        page.mouse.move(640, 400)
        page.wait_for_timeout(5600)
        self.assertEqual(current(), 1, 'slide did not move after 5 seconds with the mouse over it')
        # Clicking an arrow does not stop it either
        page.get_by_role('button', name='Next slide').click()
        self.assertEqual(current(), 2)
        page.wait_for_timeout(5600)
        self.assertEqual(current(), 0, 'slider stopped after a click')
        self.assertTrue(page.evaluate("document.querySelectorAll('.hs-slide')[1].inert"))
        self.no_sideways_scroll(page)

    def test_phone_hero_slides_match_and_quote_button_is_on_the_first_screen(self):
        for width, height in ((360, 740), (375, 812), (414, 896)):
            page = self.page({'width': width, 'height': height})
            page.emulate_media(reduced_motion='reduce')
            page.goto(self.live_server_url + '/')
            self.no_sideways_scroll(page)
            for i in range(3):
                page.locator('.hs-dot').nth(i).click()
                page.evaluate('window.scrollTo(0, 0)')
                slide = page.locator('.hs-slide').nth(i)
                quote = slide.get_by_role('link', name='Get a quote')
                expect(quote).to_be_visible()
                box = quote.bounding_box()
                self.assertLessEqual(box['y'] + box['height'], height, f'slide {i + 1} quote button below the first screen at {width}px')
                self.assertGreaterEqual(box['height'], 44, 'button too small to tap')
            # No slide leaves a big empty band: the slides' own content heights are within 40px of each other
            heights = page.evaluate("""() => [...document.querySelectorAll('.hs-slide')].map(s => {
                let bottom = 0; const top = s.getBoundingClientRect().top;
                for (const el of s.querySelectorAll('*')) { const r = el.getBoundingClientRect();
                  if (r.height && getComputedStyle(el).display !== 'none') bottom = Math.max(bottom, r.bottom - top); }
                return bottom; })""")
            self.assertLess(max(heights) - min(heights), 40, heights)

    def test_hero_slider_waits_while_a_keyboard_user_is_inside(self):
        page = self.page()
        page.goto(self.live_server_url + '/')
        page.mouse.move(1, 1)
        current = lambda: page.evaluate(
            "[...document.querySelectorAll('.hs-dot')].findIndex(d => d.getAttribute('aria-current') === 'true')")
        page.locator('.hs-slide').first.get_by_role('link').first.focus()
        page.keyboard.press('Tab')   # keyboard focus inside the slide
        page.wait_for_timeout(5600)
        self.assertEqual(current(), 0, 'slide moved away from a keyboard user')
        page.get_by_role('button', name='Next slide').focus()
        page.keyboard.press('Enter')
        self.assertEqual(current(), 1)

    def test_hero_slider_does_not_move_for_reduced_motion_users(self):
        context = self.browser.new_context(viewport=PHONE, reduced_motion='reduce')
        self.addCleanup(context.close)
        page = context.new_page()
        page.goto(self.live_server_url + '/')
        page.wait_for_timeout(5600)
        self.assertEqual(page.evaluate(
            "[...document.querySelectorAll('.hs-dot')].findIndex(d => d.getAttribute('aria-current') === 'true')"), 0)
        self.no_sideways_scroll(page)

    def test_top_bar_shows_messages_in_turn_on_phone(self):
        from core.models import SiteSettings
        s = SiteSettings.objects.first() or SiteSettings()
        s.announcement_bar = 'WE SUPPLY THE SPICE, YOU CREATE THE MAGIC.\nWE DELIVER ACROSS BRISTOL & SOUTH WEST ENGLAND'
        s.save()
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/')
        first, second = page.locator('.announcement-msg').nth(0), page.locator('.announcement-msg').nth(1)
        expect(first).to_be_visible()
        expect(second).to_be_hidden()
        page.wait_for_timeout(5800)
        expect(second).to_be_visible()
        expect(first).to_be_hidden()
        self.no_sideways_scroll(page)
        # Owner's request: each message stays on one line, even on a small 320px phone
        for width in (320, 375):
            page.set_viewport_size({'width': width, 'height': 700})
            for msg in page.locator('.announcement-msg').all():
                self.assertFalse(msg.evaluate('m => m.scrollWidth > m.clientWidth + 1'), f'cut off at {width}px')
                self.assertLess(msg.evaluate('m => m.getBoundingClientRect().height'), 24, f'wraps at {width}px')

    def test_top_bar_messages_slide_sideways(self):
        from core.models import SiteSettings
        s = SiteSettings.objects.first() or SiteSettings()
        s.announcement_bar = 'FIRST MESSAGE\nSECOND MESSAGE'
        s.save()
        page = self.page(DESKTOP)
        page.goto(self.live_server_url + '/')
        first, second = page.locator('.announcement-msg').nth(0), page.locator('.announcement-msg').nth(1)
        rest = first.evaluate('m => m.getBoundingClientRect().left')   # where a shown message sits
        page.wait_for_timeout(5250)                          # halfway through the first slide
        x1 = first.evaluate('m => m.getBoundingClientRect().left')
        x2 = second.evaluate('m => m.getBoundingClientRect().left')
        self.assertLess(x1, rest - 50)                       # the old message is moving out to the left
        self.assertGreater(x2, rest + 50)                    # the new one is coming in from the right
        page.wait_for_timeout(700)
        expect(second).to_be_visible()
        expect(first).to_be_hidden()
        self.assertAlmostEqual(second.evaluate('m => m.getBoundingClientRect().left'), rest, delta=2)
        page.wait_for_timeout(5000)                          # and round again: the first message slides back in
        expect(first).to_be_visible()
        self.no_sideways_scroll(page)

    def test_phone_taps_do_not_zoom_flash_or_leave_hover_stuck(self):
        context = self.browser.new_context(viewport=PHONE, is_mobile=True, has_touch=True)
        self.addCleanup(context.close)
        context.add_init_script(HIDE_COOKIE_POP_UP)
        page = context.new_page()
        page.goto(self.live_server_url + '/products/?q=chilli')
        # iPhones zoom the page into any box under 16px
        for size in page.locator('select').evaluate_all('els => els.map(e => getComputedStyle(e).fontSize)'):
            self.assertEqual(size, '16px')
        self.assertEqual(page.evaluate('getComputedStyle(document.documentElement).webkitTapHighlightColor'),
                         'rgba(0, 0, 0, 0)')
        card = page.locator('.card').first
        card.tap()
        page.wait_for_timeout(500)
        self.assertEqual(card.evaluate('e => getComputedStyle(e).transform'), 'none', 'hover lift stuck after a tap')
        self.no_sideways_scroll(page)

    def test_mouse_still_gets_hover_and_press_feedback(self):
        page = self.page()
        page.goto(self.live_server_url + '/products/?q=chilli')
        card = page.locator('.card').first
        card.hover()
        page.wait_for_timeout(500)
        self.assertNotEqual(card.evaluate('e => getComputedStyle(e).transform'), 'none')
        button = page.get_by_role('button', name='Enquire').first
        box = button.bounding_box()
        page.mouse.move(box['x'] + 10, box['y'] + 10)
        page.mouse.down()
        page.wait_for_timeout(200)
        self.assertIn('0.97', button.evaluate('e => getComputedStyle(e).transform'))
        page.mouse.up()

    def test_home_category_circles_and_brand_arrows(self):
        page = self.page()
        page.goto(self.live_server_url + '/')
        expect(page.locator('.sp-cat-circle')).to_have_count(2)
        track = page.locator('#brandTrack')
        expect(page.locator('.sp-brand-badge')).to_have_count(9)
        before = track.evaluate('t => t.scrollLeft')
        page.locator('.sp-slide-next').click()
        page.wait_for_function("document.getElementById('brandTrack').scrollLeft > 0")
        self.assertGreater(track.evaluate('t => t.scrollLeft'), before)
        page.locator('.sp-cat-circle', has_text='Rice').click()
        expect(page).to_have_url(self.live_server_url + '/products/?category=rice')
        expect(page.get_by_role('heading', name='Heera Basmati Rice')).to_be_visible()

    def test_header_search_finds_products_and_hides_drafts(self):
        page = self.page()
        page.goto(self.live_server_url + '/about/')
        page.fill('#navSearch', 'rice')
        page.press('#navSearch', 'Enter')
        expect(page.get_by_role('heading', name='Heera Basmati Rice')).to_be_visible()
        expect(page.get_by_role('heading', name='Hidden Draft Rice')).to_have_count(0)

    def test_phone_menu_opens(self):
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/')
        menu = page.locator('#navbarNav')
        expect(menu).to_be_hidden()
        page.locator('.navbar-toggler').click()
        expect(menu.get_by_role('link', name='Catalogue')).to_be_visible()

    def test_enquire_button_prefills_the_contact_form(self):
        page = self.page()
        page.goto(self.live_server_url + '/products/?q=chilli')
        # The box shows the 'Pack size' placeholder, so pressing Enquire without choosing sends no size
        expect(page.get_by_label('Pack size').first).to_have_value('')
        page.get_by_role('button', name='Enquire').first.click()
        expect(page.locator('#id_message')).to_have_value(
            'Hello, I am interested in wholesale pricing and availability for Heera Chilli Powder.')

    def test_choosing_a_pack_size_sends_it_to_the_enquiry_form_on_phone(self):
        PackSize.objects.create(product=self.chilli, size='6 x 1 kg', display_order=1)
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/products/?q=chilli')
        page.get_by_label('Pack size').first.select_option(label='1 kg')  # list shows weights only
        page.get_by_role('button', name='Enquire').first.click()
        expect(page.locator('#id_message')).to_have_value(
            'Hello, I am interested in wholesale pricing and availability for Heera Chilli Powder (6 x 1 kg).')

    def test_contact_form_rejects_empty_then_sends_enquiry(self):
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/contact/')
        page.get_by_role('button', name='Send Message').click()
        expect(page).to_have_url(self.live_server_url + '/contact/')   # browser keeps you on the form
        self.assertEqual(Enquiry.objects.count(), 0)

        page.fill('#id_name', 'Asha Patel')
        page.fill('#id_business_name', 'Asha Kitchen')
        page.fill('#id_email', 'asha@kitchen.example')
        page.fill('#id_phone', '0117 496 0000')
        page.fill('#id_message', 'Please quote for 20 x 1 kg basmati.')
        page.check('#id_consent_given')
        time.sleep(3.2)  # the form ignores submissions faster than a person could type
        page.get_by_role('button', name='Send Message').click()
        expect(page).to_have_url(self.live_server_url + '/wholesale/thank-you/')

        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.business_name, 'Asha Kitchen')
        subjects = [m.subject for m in mail.outbox]
        self.assertTrue(any(f'Ref {enquiry.reference}' in s for s in subjects), subjects)

    def test_unsent_enquiry_is_kept_then_cleared_once_sent(self):
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/contact/')
        page.fill('#id_name', 'Asha Patel')
        page.fill('#id_message', 'Please quote 10 x 5 kg chakki atta.')
        page.wait_for_timeout(700)                      # saved a moment after typing stops
        page.reload()                                   # e.g. the page was closed by mistake
        expect(page.locator('.sp-draft-note')).to_be_visible()
        self.assertEqual(page.input_value('#id_name'), 'Asha Patel')
        self.assertEqual(page.input_value('#id_message'), 'Please quote 10 x 5 kg chakki atta.')
        self.assertFalse(page.is_checked('#id_consent_given'))   # consent is never kept
        page.fill('#id_email', 'asha@kitchen.example')
        page.fill('#id_phone', '0117 496 0000')
        page.check('#id_consent_given')
        time.sleep(3.2)
        page.get_by_role('button', name='Send Message').click()
        expect(page).to_have_url(self.live_server_url + '/wholesale/thank-you/')
        enquiry = Enquiry.objects.get()
        expect(page.get_by_text(f'Your reference is {enquiry.reference}')).to_be_visible()
        self.assertIsNone(page.evaluate("localStorage.getItem('dr_enquiry_draft')"))
        page.goto(self.live_server_url + '/contact/')
        self.assertEqual(page.input_value('#id_name'), '')
        expect(page.locator('.sp-draft-note')).to_have_count(0)

    def test_clear_the_form_removes_kept_text(self):
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/contact/')
        page.fill('#id_message', 'Draft to throw away')
        page.wait_for_timeout(700)
        page.reload()
        page.get_by_role('button', name='Clear the form').click()
        self.assertEqual(page.input_value('#id_message'), '')
        self.assertIsNone(page.evaluate("localStorage.getItem('dr_enquiry_draft')"))

    def test_no_results_ask_us_prefills_the_enquiry(self):
        page = self.page(PHONE)
        page.goto(self.live_server_url + '/products/?q=saffron')
        page.get_by_role('link', name="Can't find it? Ask us").click()
        expect(page).to_have_url(re.compile(r'/contact/\?ask=saffron'))
        self.assertIn('"saffron"', page.input_value('#id_message'))

    def test_double_clicking_send_saves_the_enquiry_once(self):
        page = self.page(DESKTOP)
        page.goto(self.live_server_url + '/contact/')
        page.fill('#id_name', 'Ravi Shah')
        page.fill('#id_email', 'ravi@shop.example')
        page.fill('#id_phone', '0117 496 0001')
        page.fill('#id_message', 'Price for 10 x 5 kg chapatti flour please.')
        page.check('#id_consent_given')
        time.sleep(3.2)
        page.get_by_role('button', name='Send Message').dblclick()
        expect(page).to_have_url(self.live_server_url + '/wholesale/thank-you/')
        self.assertEqual(Enquiry.objects.filter(email='ravi@shop.example').count(), 1)
        to_business = [m for m in mail.outbox if 'Ravi Shah' in m.subject]
        self.assertEqual(len(to_business), 1, [m.subject for m in mail.outbox])

    def test_keyboard_users_can_reach_links_and_see_focus(self):
        page = self.page()
        page.goto(self.live_server_url + '/')
        for _ in range(3):
            page.keyboard.press('Tab')
        focused = page.evaluate("""() => {
            const el = document.activeElement, s = getComputedStyle(el);
            return {tag: el.tagName, outline: s.outlineStyle, shadow: s.boxShadow};
        }""")
        self.assertIn(focused['tag'], ('A', 'BUTTON', 'INPUT'))
        self.assertTrue(focused['outline'] != 'none' or focused['shadow'] != 'none', focused)


@tag('e2e')
@unittest.skipUnless(RUN, 'Browser tests run only with E2E=1 and Playwright installed')
@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='', NOTIFICATION_EMAIL='support@example.com',
                   GA_MEASUREMENT_ID=GA)
class CookieConsentTests(StaticLiveServerTestCase):
    """Google Analytics must not load, or set a cookie, until the visitor agrees."""

    @classmethod
    def setUpClass(cls):
        os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
        super().setUpClass()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        super().tearDownClass()

    def fresh_visitor(self, viewport=DESKTOP):
        context = self.browser.new_context(viewport=viewport)
        self.addCleanup(context.close)
        google = []
        # Record (and block) any request to Google, so the test needs no internet and sees exactly what loads
        context.route(re.compile(r'^https://[^/]*google'), lambda route: (google.append(route.request.url), route.abort()))
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        self.addCleanup(lambda: self.assertEqual(errors, [], 'JavaScript errors on the page'))
        return context, page, google

    def test_nothing_from_google_loads_before_a_choice_or_after_reject(self):
        context, page, google = self.fresh_visitor(PHONE)
        page.goto(self.live_server_url + '/')
        notice = page.locator('#cookieNotice')
        expect(notice).to_be_visible()
        page.wait_for_timeout(500)
        self.assertEqual(google, [])
        page.get_by_role('button', name='Reject All').click()
        expect(notice).to_be_hidden()
        page.goto(self.live_server_url + '/products/')
        expect(notice).to_be_hidden()                       # the choice is remembered
        page.wait_for_timeout(500)
        self.assertEqual(google, [])
        self.assertFalse([c for c in context.cookies() if c['name'].startswith('_ga')])

    def test_accept_loads_analytics_and_the_thank_you_page_counts_a_lead(self):
        context, page, google = self.fresh_visitor()
        page.goto(self.live_server_url + '/')
        page.get_by_role('button', name='Accept All').click()
        expect(page.locator('#cookieNotice')).to_be_hidden()
        page.wait_for_function('window.dataLayer && window.dataLayer.length > 0')
        self.assertTrue(any(f'googletagmanager.com/gtag/js?id={GA}' in url for url in google), google)
        page.goto(self.live_server_url + '/wholesale/thank-you/')
        page.wait_for_function('window.dataLayer && window.dataLayer.length > 0')
        events = page.evaluate('window.dataLayer.map(a => Array.from(a))')
        self.assertIn(['event', 'generate_lead'], [e[:2] for e in events])

    def test_customise_switch_and_footer_cookie_settings_change_the_choice(self):
        context, page, google = self.fresh_visitor()
        page.goto(self.live_server_url + '/')
        page.get_by_role('button', name='Customise').click()
        switch = page.get_by_role('switch', name='Analytics cookies (Google Analytics)')
        expect(switch).not_to_be_checked()                  # off unless the visitor switches it on
        switch.check()
        page.get_by_role('button', name='Save my choices').click()
        expect(page.locator('#cookieNotice')).to_be_hidden()
        page.wait_for_function('window.dataLayer && window.dataLayer.length > 0')

        # Later: change of mind from the footer link, using only the keyboard
        context.add_cookies([{'name': '_ga', 'value': 'GA1.1.1.1', 'url': self.live_server_url}])
        page.get_by_role('button', name='Cookie settings').first.focus()
        page.keyboard.press('Enter')
        expect(switch).to_be_checked()
        expect(switch).to_be_focused()
        page.keyboard.press('Space')
        page.get_by_role('button', name='Save my choices').click()
        self.assertTrue(page.evaluate(f'window["ga-disable-{GA}"]'))
        self.assertFalse([c for c in context.cookies() if c['name'].startswith('_ga')])
        page.reload()
        expect(page.locator('#cookieNotice')).to_be_hidden()
        self.assertEqual(page.evaluate('localStorage.getItem("dr_cookie_consent")'), 'denied')
