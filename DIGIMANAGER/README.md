# DigiManager — Digital Account & Social Media Management Platform

A full-stack Django platform for managing user accounts (RBAC, audit trail,
security monitoring) *and* the social-media content those accounts publish
(scheduling, AI captioning, AI image generation, analytics, reporting).

This repo is a rebuild of an existing three-month attachment project. What
changed and why is documented below — read it before you present this
as finished work; a few things are foundations, not finished features,
and that distinction matters.

---

## What this actually is

The original codebase (`DIGIMANAGER`) was a social-media post scheduler with
a thin admin/manager/creator role split. It did **not** have: an audit trail,
brute-force protection, an account directory/admin console, environment-based
secrets, or a distinct visual identity (it used unmodified Bootstrap 5
defaults). This rebuild adds all of that as a new `accounts` app layered on
top of the existing `scheduler` and `contentgen` apps, plus a full UI pass.

## Architecture

```
DIGIMANAGER/
├── accounts/          # NEW — RBAC, audit trail, login monitoring, profiles
├── scheduler/         # Custom user model, posts, platforms, dashboards
├── contentgen/        # Secondary GPT-2 caption generator
├── static/css/theme.css   # NEW — the design system
├── templates/
└── DIGIMANAGER/settings.py  # rebuilt for env-driven config
```

### Why a separate `accounts` app instead of editing `scheduler.CustomUser`

`CustomUser` already has migration history in `scheduler`. Extending it
in place risks a broken migration graph with no way to test it in this
environment (see **Not executed** below). Instead, `accounts.Profile` is a
`OneToOneField` onto `settings.AUTH_USER_MODEL` — additive, safe, and it
keeps account-management concerns in one app instead of scattered across
the app that also owns Celery task wiring for post publishing.

### Account management features (the actual ask)

| Feature | Where |
|---|---|
| Role-based access control | `accounts/decorators.py:role_required()` — centralizes what used to be duplicated `if request.user.role != 'admin'` checks in every view |
| Audit trail | `accounts/models.py:AuditLog`, populated automatically via `accounts/signals.py` (login/logout/failed-login) and `accounts/middleware.py` (every authenticated POST/PUT/PATCH/DELETE) |
| Login-attempt monitoring & brute-force lockout | `accounts/models.py:LoginAttempt`, enforced in `scheduler/views.py:login()` — configurable threshold/window via `.env` |
| Admin account directory | `accounts/views.py:account_directory` + `update_account` — change role/status per user, all changes audited |
| Security Center | `accounts/views.py:security_center` — filterable audit log + recent failed logins, admin/manager only |
| Self-service profile | `accounts/views.py:profile_view` — phone, department, bio, avatar, plus the user's own recent activity |
| 2FA readiness | `Profile.two_factor_enabled` — a flag, not a working TOTP flow. See **Known limitations**. |

### Design system

`static/css/theme.css` — a deliberate visual identity (deep slate sidebar,
indigo/teal accents, Inter typeface, KPI cards, custom data tables) applied
across every template via `templates/base.html`'s sidebar-shell layout.
Bootstrap 5 is still loaded for its grid/utility classes, but every visible
surface (buttons, forms, cards, tables, alerts, the login/register screens)
is overridden — this was **not** meant to look like default Bootstrap.

---

## Security posture (what was fixed)

The original `settings.py` had a hardcoded `SECRET_KEY` committed to the
repo, `DEBUG = True` unconditionally, and blank MySQL credentials with no
fallback. The rebuilt `settings.py`:

- Reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and DB credentials from
  environment variables (`python-decouple` + `.env`, see `.env.example`).
- Defaults to SQLite so the project runs with zero external setup; set
  `DB_ENGINE=postgres` or `DB_ENGINE=mysql` in `.env` to switch.
- Sets `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY`, `X_FRAME_OPTIONS`,
  `SECURE_CONTENT_TYPE_NOSNIFF`, and gates `SECURE_SSL_REDIRECT` /
  `*_COOKIE_SECURE` / HSTS behind env flags (off by default for local HTTP
  dev, meant to be turned on in production).
- Adds a dedicated rotating `security.log` for auth events, separate from
  the general error log.

Two other real bugs were fixed along the way (found while wiring the new
UI, not hunted for separately):

- `templates/*.html` referenced `post.title` / `post.caption` on a `Post`
  model that only has a `content` field — these would have rendered blank
  everywhere a post's text should show up.
- `contentgen.urls` and `scheduler.urls` both registered a URL named
  `generateCaption`; Django's reverse-resolution silently picked
  `scheduler`'s route for both, so the GPT-2 caption generator's "try
  another" link sent users to the wrong generator. Renamed to
  `contentgen_generateCaption` / `contentgen_captionDetail`.

## Known limitations — don't oversell these in an interview

- **Not executed.** This sandbox has no network access and no Django
  installed, so nothing here has been run. `accounts/migrations/0001_initial.py`
  is hand-written to match `accounts/models.py`, not generated by
  `makemigrations`. Run this before you touch anything else:
  ```bash
  pip install -r requirements.txt
  python manage.py makemigrations accounts   # confirm it reports "no changes"
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py runserver
  ```
  If `makemigrations` finds a diff, trust the tool's output over this file.
- **2FA is a flag, not a feature.** `Profile.two_factor_enabled` exists so
  the schema is ready; there's no TOTP secret field, no QR provisioning
  view, and no verification step in the login flow. Don't say "2FA" in a
  CV bullet unless you build that flow.
- **`accounts.Profile` rows for pre-existing users.** New logins get a
  `Profile` auto-created via a context processor. Any user created before
  this change (e.g. via fixtures) won't have one until they log in once —
  the User Directory template handles the missing-profile case gracefully,
  but run a data migration if you need it guaranteed at deploy time.
- **AI image generation stack is heavy.** `diffusers` + `torch` +
  `transformers` in `requirements.txt` are large, GPU-friendly by default,
  and slow to install/run on a laptop or small VPS. Fine for a portfolio
  demo; budget for this in any real deployment (or swap to an API-based
  image model and drop the local weights entirely).
- **Duplicate URL registrations for `generate_ai_image`** in `scheduler/urls.py`
  still exist (four patterns, same name). It works — Django resolves
  reverse() to the first zero-argument match — but it's redundant and
  worth cleaning up if you're extending this further.

---

## Roles

| Role | Can do |
|---|---|
| `admin` | Everything: user directory, security center, all dashboards, Django admin |
| `manager` | Approve/reject posts, view analytics, security center (read) |
| `creator` | Create/edit/schedule own posts, generate captions/images, manage connected platforms |

New registrations default to whatever role the register form is given —
an admin should review and adjust via **User Directory** after signup.

## Switching to PostgreSQL

The DB backend is a one-variable switch (`DB_ENGINE` in `.env`) — no code
changes needed beyond what's already in `settings.py`. Steps:

**1. Install PostgreSQL itself** (skip if you already have a server —
local, Docker, or a managed instance like RDS/Supabase/Railway all work):

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql@16 && brew services start postgresql@16

# Or Docker — no local install at all
docker run --name digimanager-pg -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=digimanager -e POSTGRES_USER=digimanager_user \
  -p 5432:5432 -d postgres:16
```

**2. Create the database and a dedicated user** (skip if you used the
Docker command above — it already did this):

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE digimanager;
CREATE USER digimanager_user WITH PASSWORD 'change-me';
ALTER ROLE digimanager_user SET client_encoding TO 'utf8';
ALTER ROLE digimanager_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE digimanager_user SET timezone TO 'Africa/Nairobi';
GRANT ALL PRIVILEGES ON DATABASE digimanager TO digimanager_user;
\q
```

**3. Install the Python driver** (already in `requirements.txt`):

```bash
pip install -r requirements.txt
# this pulls in psycopg2-binary — fine for dev; for a real production
# deploy, swap to `psycopg2` (compiled from source) instead of the
# `-binary` build, per psycopg2's own recommendation.
```

**4. Point `.env` at Postgres:**

```dotenv
DB_ENGINE=postgres
DB_NAME=digimanager
DB_USER=digimanager_user
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=5432
DB_SSLMODE=prefer      # use 'require' for any managed/remote Postgres
```

**5. Run migrations against the new database and create an admin account:**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Notes specific to Postgres:**

- `DB_SSLMODE=require` if you're connecting to a managed provider over the
  public internet (RDS, Supabase, Railway, etc.) — `prefer` is fine for
  localhost/Docker.
- `DB_CONN_MAX_AGE=60` in `.env` enables persistent connections (60s reuse
  window) instead of opening a new connection per request — meaningful
  under real load, irrelevant for local dev.
- If you're migrating *existing data* from the SQLite/MySQL version rather
  than starting fresh, don't just repoint `DB_ENGINE` — Django doesn't
  migrate data between backends automatically. Use
  `python manage.py dumpdata --natural-foreign --natural-primary > data.json`
  against the old DB, switch `.env` to Postgres, run `migrate`, then
  `python manage.py loaddata data.json` against the new one. Watch for
  `AUTO_INCREMENT`/sequence resets on `id` columns — SQLite and Postgres
  handle these differently, so check `\d+ <table>` in `psql` if inserts
  start failing on primary-key collisions after the load.



```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # edit SECRET_KEY at minimum
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Background jobs (scheduled post publishing) need Redis + a Celery worker:

```bash
celery -A DIGIMANAGER worker -l info
celery -A DIGIMANAGER beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```
