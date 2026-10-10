from django.db import migrations

def create_default_settings(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    if not SiteSettings.objects.exists():
        SiteSettings.objects.create(
            announcement_bar="WE SUPPLY THE SPICE, YOU CREATE THE MAGIC.",
            phone_number="",
            whatsapp_link="",
            email_address="support@desiroots.co.uk",
            postal_address="",
            facebook_url="",
            instagram_url="",
            linkedin_url=""
        )

def remove_default_settings(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    SiteSettings.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_settings, reverse_code=remove_default_settings),
    ]
