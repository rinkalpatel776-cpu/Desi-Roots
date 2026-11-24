"""Page speed (21 Nov 2026): small logo copies, small site logo, hero images loaded in the right order."""
import re
import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from catalogue.logo_thumbs import thumb_name
from catalogue.models import Brand

MEDIA = tempfile.mkdtemp(prefix='dr-media-test-')


def big_logo(name='big-logo.png', size=(1800, 1200)):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    for x in range(200, 1600):
        for y in range(300, 900, 40):
            img.putpixel((x, y), (200, 30, 30, 255))
    out = BytesIO(); img.save(out, 'PNG')
    return SimpleUploadedFile(name, out.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA)
class BrandLogoCopyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_uploading_a_logo_makes_a_small_webp_copy_and_keeps_the_original(self):
        brand = Brand.objects.create(name='Big Logo', slug='big-logo', logo=big_logo(), is_featured=True)
        original = Path(MEDIA) / brand.logo.name
        small = Path(MEDIA) / thumb_name(brand.logo.name)
        self.assertTrue(original.exists())
        self.assertTrue(small.exists())
        with Image.open(small) as img:
            self.assertEqual(img.format, 'WEBP')
            self.assertLessEqual(max(img.size), 320)
        self.assertLess(small.stat().st_size, original.stat().st_size)

    def test_pages_show_the_small_copy(self):
        brand = Brand.objects.create(name='Big Logo', slug='big-logo', logo=big_logo(), is_featured=True, home_order=1)
        url = settings.MEDIA_URL + thumb_name(brand.logo.name)
        self.assertContains(self.client.get('/brands/'), url)
        self.assertNotContains(self.client.get('/brands/'), settings.MEDIA_URL + brand.logo.name)

    def test_missing_copy_falls_back_to_the_original(self):
        brand = Brand.objects.create(name='Big Logo', slug='big-logo', logo=big_logo())
        (Path(MEDIA) / thumb_name(brand.logo.name)).unlink()
        self.assertContains(self.client.get('/brands/'), settings.MEDIA_URL + brand.logo.name)
        call_command('make_logo_thumbs', stdout=StringIO())
        self.assertTrue((Path(MEDIA) / thumb_name(brand.logo.name)).exists())


class SiteSpeedTests(TestCase):
    def test_header_footer_and_about_use_the_small_site_logo(self):
        for path in ('/', '/about/'):
            html = self.client.get(path).content.decode()
            self.assertNotIn('images/logo.png', html, path)
        self.assertLess((Path(settings.BASE_DIR) / 'static/images/logo-160.webp').stat().st_size, 20_000)

    def test_hero_loads_the_first_picture_first_and_skips_hidden_ones(self):
        html = self.client.get('/').content.decode()
        phone_img = html[html.index('class="hs-m-img"'):][:600]
        self.assertIn('fetchpriority="high"', phone_img)
        self.assertNotIn('loading="lazy"', phone_img)                 # never lazy-load what shows first
        self.assertIn('rel="preload" as="image"', html)               # computers: slide 1's background photo
        self.assertEqual(html.count('<source media='), 3)              # hidden pictures get a 1-pixel placeholder
        self.assertEqual(html.count('fetchpriority="low"'), 3)         # later slides wait their turn

    def test_no_template_note_spans_two_lines(self):
        # Django only hides {# ... #} notes on one line; longer ones show up on the page as text
        for path in Path(settings.BASE_DIR, 'templates').rglob('*.html'):
            if ' 2.' in path.name or ' 3.' in path.name:
                continue  # stray sync copies, not used
            text = path.read_text()
            bad = [m.group(0)[:60] for m in re.finditer(r'\{#(.*?)#\}', text, re.S) if '\n' in m.group(1)]
            self.assertEqual(bad, [], path)


def category_photo(name='spices-circle.png', size=(400, 400)):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    for x in range(40, 360, 3):
        for y in range(40, 360, 3):
            img.putpixel((x, y), ((x * 7) % 255, (y * 5) % 255, 120, 255))
    out = BytesIO(); img.save(out, 'PNG')
    return SimpleUploadedFile(name, out.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA)
class CategoryPhotoCopyTests(TestCase):
    """Smaller category photos on phones (24 Nov 2026): a 240 px WebP copy offered through srcset."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def make_category(self):
        from catalogue.models import Category, Product
        cat = Category.objects.create(name='Spices', slug='spices', show_on_home=True, image=category_photo())
        Product.objects.create(name='Heera Chilli Powder', slug='hcp', category=cat, is_published=True)
        return cat

    def test_uploading_a_photo_makes_a_small_webp_copy_and_keeps_the_original(self):
        from catalogue.category_thumbs import thumb_name as cat_thumb
        cat = self.make_category()
        original = Path(MEDIA) / cat.image.name
        small = Path(MEDIA) / cat_thumb(cat.image.name)
        self.assertTrue(original.exists())
        with Image.open(small) as img:
            self.assertEqual(img.format, 'WEBP')
            self.assertEqual(max(img.size), 240)
        self.assertLess(small.stat().st_size, original.stat().st_size)

    def test_home_offers_the_small_copy_to_phones_and_the_original_to_computers(self):
        from catalogue.category_thumbs import thumb_name as cat_thumb
        cat = self.make_category()
        html = self.client.get('/').content.decode()
        tag = re.search(r'<img [^>]*alt="Spices product packs"[^>]*>', html).group(0)
        small = settings.MEDIA_URL + cat_thumb(cat.image.name)
        original = settings.MEDIA_URL + cat.image.name
        self.assertIn(f'src="{original}"', tag)
        self.assertIn(f'srcset="{small} 240w, {original} 400w"', tag)
        self.assertIn('sizes="(max-width: 575.98px) 18vw', tag)  # 18vw, not the real ~30vw: caps phones at 2x so 3x iPhones get the small copy too
        self.assertIn('loading="lazy"', tag)

    def test_missing_copy_falls_back_to_the_original_and_the_command_remakes_it(self):
        from catalogue.category_thumbs import thumb_name as cat_thumb
        cat = self.make_category()
        (Path(MEDIA) / cat_thumb(cat.image.name)).unlink()
        tag = re.search(r'<img [^>]*alt="Spices product packs"[^>]*>', self.client.get('/').content.decode()).group(0)
        self.assertNotIn('srcset', tag)
        self.assertIn(f'src="{settings.MEDIA_URL + cat.image.name}"', tag)
        call_command('make_category_thumbs', stdout=StringIO())
        self.assertTrue((Path(MEDIA) / cat_thumb(cat.image.name)).exists())
