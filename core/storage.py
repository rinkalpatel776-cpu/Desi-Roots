"""Static files with content-hashed names on the live server (24 Nov 2026).

collectstatic writes each CSS/JS/image file twice: under its plain name and under a name that
contains a hash of its contents (style.css -> style.3f9a1c2b7d4e.css). Pages link to the hashed
name, so browsers can keep a file for a year: an edited file gets a new name automatically.

Two safety changes from the standard storage:
- "sourceMappingURL" comments are left alone. The Bootstrap files name .map helper files that we
  don't ship, and rewriting those comments would also change the files' contents and break their
  integrity (SRI) hashes in base.html.
- A file that is missing from the list never causes a server error: the page links to the plain
  name instead.
"""
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage, StaticFilesStorage
from whitenoise.storage import CompressedManifestStaticFilesStorage


def _without_source_maps(patterns):
    kept = []
    for glob, rules in patterns:
        rules = tuple(r for r in rules if 'sourceMappingURL' not in (r[0] if isinstance(r, tuple) else r))
        kept.append((glob, rules))
    return tuple(kept)


class DesiRootsStaticStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
    patterns = _without_source_maps(ManifestStaticFilesStorage.patterns)

    def url(self, name, force=False):
        try:
            return super().url(name, force)
        except ValueError:
            return StaticFilesStorage.url(self, name)   # the plain, unhashed address
