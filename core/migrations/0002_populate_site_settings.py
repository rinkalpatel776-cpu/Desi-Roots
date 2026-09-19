from django.db import migrations

def create_default_settings(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    if not SiteSettings.objects.exists():
        SiteSettings.objects.create(
            announcement_bar="WE SUPPLY THE SPICE, YOU CREATE THE MAGIC.",
            phone_number="+44 117 000 0000",
            whatsapp_link="https://wa.me/447000000000",
            email_address="support@desiroots.co.uk",
            postal_address="Desi Roots / Spice Pantry\nBristol, United Kingdom",
            facebook_url="https://facebook.com/spicepantry",
            instagram_url="https://instagram.com/spicepantry",
            linkedin_url="https://linkedin.com/company/spicepantry"
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
