---
name: wordpress
description: WordPress security testing — vulnerable plugins/themes, user enumeration, XML-RPC/REST abuse, auth and privilege escalation, and the plugin-driven RCE/SQLi that dominates real incidents
---

# WordPress

Security testing for WordPress. Core is relatively hardened; **plugins and themes** are
where almost every real breach happens. Fingerprint core + every plugin/theme version,
then map each to known vulnerabilities before manual testing.

## Fingerprinting

- `/wp-login.php`, `/wp-admin/`, `/wp-json/`, `/xmlrpc.php`, `/readme.html`, `/wp-cron.php`.
- Version: `<meta name="generator" content="WordPress X.Y">`, `readme.html`, `/wp-includes/` asset `?ver=`.
- Plugins/themes: `/wp-content/plugins/<slug>/` + `readme.txt` (version), `/wp-content/themes/<slug>/style.css`.
- Users: `/wp-json/wp/v2/users`, `/?author=1`, login error differences.

## Attack Surface

- **Plugins / themes**: the dominant surface — SQLi, RCE, arbitrary file upload/download,
  auth bypass, privilege escalation, CSRF, SSRF.
- **REST API** (`/wp-json/`): user enumeration, unauthenticated data, plugin REST routes.
- **XML-RPC** (`/xmlrpc.php`): `system.multicall` password brute-force amplification, pingback SSRF/DDoS.
- **Auth**: weak creds, user enumeration, nonce/capability misuse, password reset flaws.
- **Uploads / media**: unrestricted file upload → webshell in `/wp-content/uploads/`.
- **wp-config / backups**: `wp-config.php.bak`, `.sql` dumps, `/wp-content/debug.log`.

## Reconnaissance

```bash
# Version + user enumeration
curl -s "$TARGET/" | grep -i 'name="generator"'
curl -s "$TARGET/wp-json/wp/v2/users" | head
curl -s "$TARGET/?author=1" -I | grep -i location   # redirects to /author/<username>/

# Enumerate plugins/themes + versions (readme.txt), then map to known CVEs
for p in woocommerce elementor contact-form-7 wpforms yoast-seo; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "$TARGET/wp-content/plugins/$p/readme.txt"; done

# Exposure checks
for f in wp-config.php.bak wp-config.php~ .env wp-content/debug.log xmlrpc.php; do
  curl -s -o /dev/null -w "%{http_code} /$f\n" "$TARGET/$f"; done
```

- `wpscan` (with an API token) automates plugin/theme → CVE mapping; mirror it manually.

## Key Vulnerabilities

### Vulnerable plugins / themes (primary)
Enumerate every plugin/theme + exact version, map to known advisories (SQLi, auth bypass,
arbitrary upload, RCE, LFI, SSRF). Outdated, abandoned, or nulled plugins are the usual way in.

### User enumeration → brute force
- REST `/wp-json/wp/v2/users`, `?author=N`, login/reset message differences reveal usernames.
- XML-RPC `system.multicall` tries many passwords per request (bypasses naive rate limits).

### XML-RPC abuse
- `pingback.ping` → SSRF / reflected DDoS against third parties.
- Brute-force amplification via `system.multicall`. Often should be disabled.

### Privilege escalation / auth bypass
- Plugin capability checks missing (`current_user_can`), nonce reuse/CSRF on admin actions.
- Subscriber → admin via vulnerable plugin AJAX/REST endpoints.

### Arbitrary file upload / RCE
- Plugin upload handlers without type checks → PHP webshell in `uploads/`.
- Theme/plugin editor (if reachable) → write PHP → RCE.

### Sensitive file exposure
- `wp-config.php` backups, `.sql` dumps, `debug.log` (leaks creds/keys/paths).

## Testing Methodology

1. Fingerprint core + enumerate **all** plugins/themes with exact versions.
2. Map each version to known advisories; prioritize unauth RCE/SQLi/auth-bypass.
3. Enumerate users (REST/author/login) → targeted brute force (respect scope).
4. Test XML-RPC (multicall, pingback) if enabled.
5. Probe upload/media handlers and admin AJAX/REST for authz + file-type gaps.
6. Check for exposed `wp-config` backups, dumps, debug.log.

## Validation Requirements

- For a vulnerable plugin, prove the specific issue (SQLi data, uploaded file executing,
  the privileged action performed) — not just the presence of a known-vulnerable version.
- User enumeration: list the real usernames obtained.
- RCE/upload: show the webshell/command output from a benign proof; then remove any
  uploaded artifact.
- Keep brute force and pingback tests within authorized scope and non-abusive.
