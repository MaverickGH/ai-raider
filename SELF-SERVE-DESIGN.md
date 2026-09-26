# AI-Raider as a self-serve service: ownership verification + sandbox network scope

[Русский](SELF-SERVE-DESIGN.ru.md) · **English**

Design spec. How to open autonomous pentesting to Cyber Galaxy users so that each one
can scan **only their own** resources, the service is not tied to the owner account, and
a running agent physically cannot reach other hosts.

Status: design. Not yet implemented — this is the contract to build against.

---

## 1. Why, and the threat model

AI-Raider is an offensive tool: a team of agents inside a Docker sandbox runs arbitrary
code and network requests against the target. Opening such "click and scan" to outsiders
is only safe with two guarantees:

1. **Target authorization** — the user has proven the target belongs to them.
2. **Network scope** — even if the agent wanted to, it cannot reach anything but the
   proven target and the model endpoint.

Threat model:

| Threat | Consequence | Mitigated in |
|---|---|---|
| Scanning someone else's site/repo | Illegal attack from our IP, liability on the platform | §3 verification + §4 scope |
| Agent leaves for a third-party host (pivot, exfiltration) | Platform as an attack proxy | §4 egress allowlist |
| SSRF into cloud metadata (169.254.169.254) | Theft of infra credentials | §4 block metadata/private |
| DNS rebinding: domain proven, then repointed to another IP | Scanning someone else's host under your name | §4 IP pinning + §3 re-check at launch |
| Domain changed owner after verification | Scanning a resource that is no longer yours | §3 expiry + re-check |
| Runaway cost / infinite loop | Budget drain, denial of service | §4 cost/time limits |
| Owner credential leak via the shared import channel | Admin compromise | §2 per-job token instead of owner cookie |

Principle: **verify at the UI, enforce at the network.** A UI grant is necessary but not
sufficient; the real boundary is the network, outside the sandbox's control.

---

## 2. Multi-tenant model (not tied to the owner)

Today the whole path is owner-only: findings are sent to `POST /api/admin/pentest` with
the owner cookie `cg_auth`. For self-serve this changes:

- **The actor is an ordinary authenticated platform user**, not the owner. Launching a
  scan and viewing one's own findings is available to any logged-in user.
- **Owner rights are needed only** for the global catalog of all runs (admin overview)
  and moderation. The owner's personal credentials are not involved in user scans at all.
- **Findings import uses a per-job service token**, not the owner cookie. The run
  orchestrator gets a short-lived signed job token; the server maps token → job → user
  and writes findings under their `uid`. The owner is out of the chain.
- Even cleaner: the **platform worker writes to the DB directly** under the job's
  `owner_uid`, without an HTTP self-call. Then a token is only needed if the worker and
  the platform are separate.

Result: the service is multi-tenant, everyone sees their own, and there is no "tied to
me" — as the owner I only administer, I am not a technical point every scan passes
through.

---

## 3. Target ownership verification

An ownership grant = a record `(user_uid, kind, scope, method, token, status,
verified_at, expires_at, evidence)`. Until a grant is `verified`, launching is impossible.

### 3.1 Web target (domain/URL)

The user adds a target → the platform issues a token `cg-verify=<random>` and one of two
checks (like Google Search Console):

1. **DNS TXT** — a `cg-verify=<token>` TXT record at `_cyber-galaxy.<domain>` (or the
   apex). The platform resolves and compares. Plus: needs no site access.
2. **HTTP file** — a file `https://<domain>/.well-known/cyber-galaxy-verification.txt`
   with the token inside. The platform does a GET and compares. Plus: simple for those
   with no DNS access.

Grant scope = the **exact origin** (scheme+host+port) that was proven. Subdomains — only
explicitly added and **each proven separately** (no wildcards at the start: owning the
apex does not mean owning an arbitrary subdomain that may have been delegated).

### 3.2 Repository (code)

- **MVP, simple:** a `cyber-galaxy-verification.txt` file with the token at the root of
  the default branch. The platform reads the raw content and compares. Works for private
  repos too via an access token the user provided when connecting.
- **Better, for GitHub:** GitHub OAuth → check that the user has `admin`/`push` on the
  specific repository. Then ownership = permissions, no file needed.

Grant scope = the specific repository and (optionally) branch/commit.

### 3.3 Expiry and re-check (TOCTOU)

- A grant lives for a limited time (e.g. **90 days**), then requires re-verification.
- **Before every launch** the platform does a cheap re-check of the token
  (DNS/HTTP/permissions). This closes "proved → sold the domain → scans someone else's".
- For web, the resolved IP is pinned at launch (see §4) — DNS rebinding between the check
  and the scan does not help.
- The user or an admin can **revoke** a grant; active jobs under it are killed.

---

## 4. Sandbox network scope (the security core)

### 4.1 Why you cannot confine from inside the container

In `airaider/runtime/docker_client.py` the sandbox is given the `NET_ADMIN` and
`NET_RAW` capabilities (needed by pentest tools). So the container **can change its own
iptables/routes** and strip any rules set inside. Conclusion: confining egress from
inside the sandbox is useless. The boundary must be outside its network namespace.

Also, `host.docker.internal` → host-gateway is currently passed into the container
(`docker_client.py:232-233`). Convenient for trusted local scans, but for outside users
it is a **direct path to the host** — in self-serve mode we remove it.

### 4.2 Scheme: a per-scan network + egress gateway

For each job:

```
                        +---------------------------------------+
                        |  per-scan Docker network (internal)   |
                        |                                       |
   [sandbox container] -+--> [egress-gateway container] --> internet (allowlist only)
   NET_ADMIN/NET_RAW    |     iptables/nftables outside         |
   but no way out       |     the sandbox's control             |
                        +---------------------------------------+
```

- The sandbox attaches to an **`--internal` Docker network** with no route out. It cannot
  reach the internet on its own, whatever it does to its iptables.
- The only exit is through the **egress gateway** (a separate gateway container) with
  default-deny and an allowlist. Its rules live in its namespace; the sandbox cannot
  touch them.
- The gateway matches by **destination IP:port**, not by hostname (otherwise DNS
  rebinding).

### 4.3 What is on the allowlist

Exactly two classes of destinations, everything else is dropped:

1. **The grant's target**, resolved to IP at job start and **pinned**:
   - web: `IP(host):port` of the proven origin;
   - repo: the git-hosting host (github.com and its CDN).
2. **The model endpoint** — a fixed, platform-controlled list (`api.openai.com`,
   `openrouter.ai`, `generativelanguage.googleapis.com`, local Ollama, etc.), depending
   on the chosen provider.

Explicitly **always dropped**, even if it accidentally ends up in the target:

- Cloud metadata: `169.254.169.254`, `fd00:ec2::254`, `metadata.google.internal`.
- Private/loopback/link-local: `10/8`, `172.16/12`, `192.168/16`, `127/8`, `169.254/16`,
  `::1`, `fc00::/7`, `fe80::/10`.
- The host and the platform's internal network, `host.docker.internal`, the import
  endpoint itself.

If the proven origin resolves to a private IP — we do not launch the job (it is either an
internal resource or an attempt to bypass the scope).

### 4.4 Per-run limits

- **Time** — a hard wall-clock timeout; on expiry the containers are killed (a kill
  already exists in `docker_client.py`).
- **Cost** — a hard cap on tokens/money; on exceeding it the job stops. Accounting is
  already collected (`llm_usage` in `run.json`).
- **CPU/RAM/PIDs** — via the existing `AIRAIDER_SANDBOX_MEM_LIMIT`,
  `AIRAIDER_SANDBOX_CPUS`, `AIRAIDER_SANDBOX_PIDS_LIMIT` (`docker_client.py:69-90`).
- **Rate limit** — N concurrent and M/day scans per user.
- Container: not privileged, `--read-only` rootfs where possible, target code mounted
  read-only, drop extra caps.

### 4.5 Integration points in the ai-raider code

- `_apply_sandbox_network()` (`docker_client.py:62`) already switches the network via
  `AIRAIDER_DOCKER_SANDBOX_NETWORK`. The orchestrator creates a per-scan `--internal`
  network and passes its name here.
- Make the `host.docker.internal` injection (`docker_client.py:232-233`) conditional: in
  self-serve mode (e.g. `AIRAIDER_SELF_SERVE=1`) do not add the host-gateway.
- The egress gateway and its nftables allowlist — a new orchestrator component (outside
  the sandbox image). It gets the allowed `host:port` list from the platform per job.
- Findings import: `scripts/push_findings.py` accepts `CG_JOB_TOKEN` instead of
  `CG_AUTH_COOKIE` and sends `Authorization: Bearer <job-token>` (or the worker writes to
  the DB directly).

---

## 5. End-to-end flow

1. **Add a target.** The user enters a domain/URL or repository → a `pending` grant +
   token + verification instructions.
2. **Verification.** The user sets a DNS TXT / well-known file / repo file → clicks
   "Verify" → the grant becomes `verified` (with expiry).
3. **Launch.** The user picks a mode (quick/standard/deep) within budget → a `scan_job`
   is created in the queue. Explicit consent to test (ToS) is recorded.
4. **Re-check + scope.** The worker takes the job → re-checks ownership → resolves and
   pins the target IP → brings up a per-scan `--internal` network + egress gateway with
   an allowlist (target + model) → launches the sandbox.
5. **Run.** The agents work and write the run directory. Anything off the allowlist is cut
   and logged by the gateway.
6. **Collect findings.** The worker collects `vulnerabilities.json` + report → writes to
   the DB under the job's `owner_uid` (or pushes with the job token).
7. **Cabinet.** Findings and report appear for the user. A per-job audit is kept.

---

## 6. Data (platform)

New/changed tables (Supabase, with RLS):

- `scan_target_grants` — `id, user_uid, kind(web|repo), scope(origin|repo url),
  method(dns|http|repo-file|github-oauth), token, status(pending|verified|expired|
  revoked), verified_at, expires_at, evidence(jsonb)`.
- `scan_jobs` — `id, user_uid, grant_id, target, scan_mode, status(queued|running|done|
  failed|killed), cost, budget_cap, egress_allow(jsonb), started_at, finished_at`.
- `pentest_runs` / `pentest_findings` — add `owner_uid` (the run's owning user). RLS: a
  user sees only their own rows; owner/editor — all.
- Audit: reuse `admin_audit_events` + a per-user job log; log egress-deny events (a signal
  of abuse or a compromised agent).

Endpoints (roughly):

- `POST /api/targets` — add a target, return token/instructions.
- `POST /api/targets/:id/verify` — run the ownership check.
- `POST /api/scans` — enqueue a job (only on a `verified` grant, within limits).
- `GET /api/scans/:id` — a job's status/findings (own only).
- The existing `POST /api/admin/pentest` stays for owner import; for self-serve — a write
  under the job's `owner_uid` with the job token.

---

## 7. Split across repositories

| Component | Where | What to do |
|---|---|---|
| Ownership verification, grants, queue, cabinet | platform (Cyber Galaxy) | new tables, endpoints, UI |
| Worker: re-check, per-scan network, egress gateway, limits, findings collection | platform/infra (a new service) | Docker runner orchestration |
| Conditional host-gateway, accepting the per-scan network name | ai-raider (`docker_client.py`) | flag `AIRAIDER_SELF_SERVE`, points in §4.5 |
| Import via job token | ai-raider (`scripts/push_findings.py`) | `CG_JOB_TOKEN` → Bearer |

---

## 8. Security and abuse (checklist)

- [ ] Launch only on a `verified` grant, re-check at start.
- [ ] Egress default-deny, allowlist by IP, target IP pinning.
- [ ] Block metadata/private/loopback/host, refuse if the target resolves to a private IP.
- [ ] Hard cap on cost and time, kill on exceeding.
- [ ] Rate limit scans per user.
- [ ] Explicit consent to test (ToS) with a "who authorized" record.
- [ ] Grant revocation → kill active jobs.
- [ ] Findings under the user's `uid`, RLS, owner credentials out of the chain.
- [ ] Logging of egress-deny and all launches.
- [ ] Default to code and staging; production targets with an explicit warning.

---

## 9. Rollout stages

1. **Sandbox scope (ai-raider).** Flag `AIRAIDER_SELF_SERVE`: remove host-gateway, accept
   the `--internal` network name. An egress-gateway prototype with an allowlist. Verify
   that the sandbox cannot reach anything but the target and the model, even while trying
   to edit its own iptables.
2. **Ownership verification (platform).** Grants + DNS TXT / well-known / repo-file,
   expiry and re-check.
3. **Queue and worker.** `scan_jobs`, Docker runner orchestration, cost/time limits,
   findings collection under `owner_uid`.
4. **User cabinet.** Job list, statuses, reports and findings; RLS.
5. **Polish.** Rate limit, ToS consent, grant revocation, egress-deny dashboard.

MVP "safely open to people" = stages 1–3. Stage 1 is the riskiest technically and must be
closed and verified first.
