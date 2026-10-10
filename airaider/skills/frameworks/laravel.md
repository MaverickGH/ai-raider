---
name: laravel
description: Laravel (PHP) security testing — debug mode / Ignition RCE, APP_KEY and cookie decryption, mass assignment, SQL injection via raw/relations, SSTI in Blade, and exposed env
---

# Laravel (PHP)

Security testing for Laravel apps. The highest-impact bugs come from leaked `APP_KEY`,
debug mode (`APP_DEBUG=true`) with Ignition, exposed `.env`, and mass assignment. Confirm
version and debug state first — they decide the whole engagement.

## Fingerprinting

- Cookies: `laravel_session`, `XSRF-TOKEN`, `<app>_session`.
- Headers: `Set-Cookie` with the above; `X-Powered-By: PHP`.
- Error page: Ignition (Whoops-style) with "Laravel" + version, stack traces.
- Paths: `/.env`, `/storage/logs/laravel.log`, `/telescope`, `/horizon`, `/_ignition/health-check`.

## Attack Surface

- **Debug mode**: Ignition error page leaking env, queries, source; historically RCE.
- **`APP_KEY`**: signs/encrypts cookies and signed URLs — leak = session forgery + deserialization.
- **Mass assignment**: `Model::create($request->all())` without `$fillable`/`$guarded`.
- **Eloquent/DB**: `whereRaw`, `DB::raw`, `orderByRaw`, dynamic column names → SQLi.
- **Blade templates**: `{!! !!}` unescaped output (XSS); server-side template eval (SSTI).
- **Signed/temporary URLs**: forgeable if `APP_KEY` leaks.
- **Dev tooling**: Telescope, Horizon, debugbar exposed in prod.

## Reconnaissance

```bash
curl -s "$TARGET/.env" | head                 # leaked env: APP_KEY, DB creds, mail, AWS
curl -s "$TARGET/_ignition/health-check"       # Ignition present → debug on
curl -s -o /dev/null -w "%{http_code}\n" "$TARGET/telescope"   # dev panel exposed?
curl -s "$TARGET/storage/logs/laravel.log" | tail   # stack traces, queries, PII
```

- An error-triggering request + `APP_DEBUG=true` → Ignition reveals env, DB queries, code.
- Grep a leaked `.env` for `APP_KEY`, `DB_*`, `AWS_*`, `MAIL_*`, `*_SECRET`.

## Key Vulnerabilities

### Debug mode / Ignition
- `APP_DEBUG=true` exposes env + queries + source on any error.
- **CVE-2021-3129**: Ignition `executeSolution` → RCE on vulnerable `facade/ignition`
  with debug on (confirm version). Classic Laravel RCE.

### APP_KEY compromise → cookie/session forgery & deserialization
- Leaked `APP_KEY` lets you encrypt/sign arbitrary cookies and signed URLs.
- Laravel decrypts the session cookie then **unserializes** it → PHP object injection /
  gadget-chain RCE when a gadget exists. Also forge `remember_me` and signed routes.

### Mass assignment
`$model->fill($request->all())` or `create($request->all())` without `$guarded`/`$fillable`
→ set `is_admin`, `role_id`, `email_verified_at`, foreign keys. See `mass_assignment`.

### SQL injection
- `whereRaw("... $input")`, `DB::raw`, `orderByRaw`, and **dynamic column/table names**
  (not bound by Eloquent) → injection. Validate ordering/column params especially.

### Blade SSTI / XSS
- `{!! $userInput !!}` renders unescaped → stored/reflected XSS.
- `Blade::render($userInput)` or compiling user templates → SSTI → RCE.

### Exposed dev endpoints
- Telescope/Horizon/debugbar in prod leak requests, queries, jobs, secrets.

## Testing Methodology

1. Fingerprint Laravel + version; check `APP_DEBUG` (Ignition) and `/.env`.
2. If `.env`/`APP_KEY` leaks → forge cookies/signed URLs; test session deserialization.
3. Match version for Ignition RCE (CVE-2021-3129) and other advisories.
4. Test mass assignment on create/update endpoints.
5. Probe raw-query and dynamic-column params for SQLi; Blade sinks for XSS/SSTI.
6. Check Telescope/Horizon/debugbar exposure.

## Validation Requirements

- Leaked `.env`/`APP_KEY`: prove impact (forge a valid session/signed URL), not just the file.
- RCE (Ignition/deserialization/SSTI): show command output or an out-of-band callback from a
  benign payload.
- Mass assignment: show the privileged field actually changed server-side.
- Keep proofs non-destructive on production.
