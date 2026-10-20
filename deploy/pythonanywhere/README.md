# Spice Pantry on PythonAnywhere (free plan)

An always-on copy of the site at `https://<username>.pythonanywhere.com`. It keeps
working when the Mac is off. Search engines are asked not to index it
(`SITE_NOINDEX=True` in `.env`).

What the free plan cannot do:

- **No outgoing email.** Enquiries are still saved; read them in the admin.
- **MySQL only.** The site uses MySQL here and PostgreSQL everywhere else.
- **Renewal.** Log in and click **"Run until 3 months from today"** on the Web tab
  at least once every three months, or the site is switched off.
- **About 512 MB of disk**, which is enough for the code and the current photos.

## You need

`spice-pantry-pythonanywhere.zip`, which contains the code, the photos and a
one-time data file. The data file includes staff login hashes, so don't share
the zip.

## 1. Databases tab

1. Set a MySQL password and note it down. This is not your account password.
2. Under "Create a database", type `spicepantry` and click Create.
   The database shows as `<username>$spicepantry`.

## 2. Files tab

Upload `spice-pantry-pythonanywhere.zip` to `/home/<username>/`.

The free plan's upload limit is 100 MB. If the zip is bigger, upload it in parts.
See "Big uploads" below.

## 3. Bash console

On the Consoles tab, start a **Bash** console and run:

```bash
cd ~ && unzip -q spice-pantry-pythonanywhere.zip -d spice-pantry && rm spice-pantry-pythonanywhere.zip
cd ~/spice-pantry && bash deploy/pythonanywhere/setup.sh
```

The script:

1. Asks for the MySQL password. Nothing shows while you type.
2. Asks for a private admin address, for example `sp-portal-7k3q9`.
3. Installs the packages.
4. Creates the tables.
5. Loads the products, then deletes the data file.
6. Prints the product counts and the values for the Web tab.

Note which Python version it says it used.

## 4. Web tab

1. Click **Add a new web app**, choose **Manual configuration** (not "Django"),
   and pick **the same Python version** the script used.
2. Fill in these settings:

   | Setting | Value |
   |---|---|
   | Source code | `/home/<username>/spice-pantry` |
   | Working directory | `/home/<username>/spice-pantry` |
   | Virtualenv | `/home/<username>/.virtualenvs/spicepantry` |

3. Click the **WSGI configuration file** link. Delete everything in it, paste in
   the contents of `deploy/pythonanywhere/wsgi.py`, and save. If your username
   is not `mantra1424`, change `PROJECT_DIR` to match.
4. Add two **Static files** entries:

   | URL | Directory |
   |---|---|
   | `/static/` | `/home/<username>/spice-pantry/staticfiles` |
   | `/media/` | `/home/<username>/spice-pantry/media` |

5. Turn on **Force HTTPS**.
6. Click the green **Reload** button.

## 5. Check it

1. Open `https://<username>.pythonanywhere.com`. You should see the home page
   with photos.
2. Open `/products/` and try a search.
3. Open `https://<username>.pythonanywhere.com/<admin path>/` and log in with
   your usual staff account.
4. If something fails, check the **error log** link on the Web tab and send me
   the last lines.

## Updating later

Upload the changed files on the Files tab, or a fresh code zip, and unzip it
over the folder. Then run:

```bash
cd ~/spice-pantry && source ~/.virtualenvs/spicepantry/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.pythonanywhere
python manage.py migrate && python manage.py collectstatic --noinput
```

Then click **Reload** on the Web tab.

Products, photos and Site Settings edited in this site's admin live only on
PythonAnywhere. They are not copied back to the Mac.

## Big uploads

To split the zip on the Mac:

```bash
split -b 90m spice-pantry-pythonanywhere.zip sp-part-
```

Upload every `sp-part-*` file. Then, in the Bash console, rejoin them before
step 3:

```bash
cd ~ && cat sp-part-* > spice-pantry-pythonanywhere.zip && rm sp-part-*
```
