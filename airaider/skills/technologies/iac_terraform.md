---
name: iac_terraform
description: Infrastructure-as-Code security review (Terraform, CloudFormation, Kubernetes manifests) — misconfigurations, secrets in code/state, insecure defaults, module/provider supply chain, and state exposure
---

# IaC / Terraform

Security review of Infrastructure-as-Code: Terraform (`.tf`, `.tfvars`), CloudFormation,
and Kubernetes manifests/Helm. This is source-aware (white-box) — the goal is to catch the
misconfiguration or leaked secret in the code and state before it ships to the cloud.
Pair with the `aws`/`azure`/`gcp`/`kubernetes` packs for the runtime side.

## Attack Surface

- **Resource misconfigurations**: public storage, open security groups, unencrypted data,
  permissive IAM, disabled logging.
- **Secrets**: hardcoded keys/passwords in `.tf`/`.tfvars`, and secrets stored in plaintext
  in **state** (`terraform.tfstate`).
- **State files**: local or remote state exposure (S3/HTTP backend), no encryption/locking.
- **Supply chain**: untrusted modules (registry/git), unpinned providers/modules, provider
  typosquatting, `terraform` running attacker-controlled code at plan time.
- **Policy gaps**: no `tfsec`/`checkov`/OPA gate; drift from the reviewed code.

## Reconnaissance

```bash
# Secrets in IaC and state
grep -rniE "password|secret|api[_-]?key|token|private_key|-----BEGIN" --include="*.tf" --include="*.tfvars" --include="*.json" .
grep -rniE "access_key|secret_key|aws_secret|client_secret" --include="*.tfstate*" .

# Backend + provider/module sourcing
grep -rniE "backend \"(s3|http|azurerm|gcs)\"|source *=|version *=" --include="*.tf" .

# Fast static scanners (confirm findings manually)
# tfsec .      checkov -d .      terrascan scan      kube-score / kubesec for manifests
```

- Check VCS history for committed `*.tfstate`, `*.tfvars`, `.env` (secrets persist in git).
- Identify the state backend and whether it is world/over-broadly readable.

## Key Vulnerabilities

### Insecure resource defaults
- **Public storage**: S3 `acl=public-read`/`public-read-write`, GCS allUsers, Azure public blobs.
- **Open ingress**: security groups / NSGs with `0.0.0.0/0` to 22/3389/db ports.
- **Unencrypted**: disks/buckets/RDS without encryption; no TLS enforcement.
- **No logging/audit**: CloudTrail/flow logs/audit disabled.
- **Public exposure**: DBs/clusters with public IPs/endpoints.

### Over-privileged IAM
- Policies with `Action:"*"`, `Resource:"*"`, `*:*` roles, `AdministratorAccess` attached
  broadly, wildcard trust policies (`Principal:"*"`), privilege-escalation-prone permissions.

### Secrets in code and state
- Hardcoded credentials in `.tf`/`.tfvars` (and thus in git).
- **State leaks**: `terraform.tfstate` stores resource attributes incl. generated secrets
  (RDS passwords, keys) in plaintext → protect, encrypt, and never commit it.

### State backend exposure
- S3/GCS/HTTP backend without encryption, versioning, or least-privilege access; no state
  locking (DynamoDB/lease) → tampering/race.

### Supply chain
- Modules from untrusted registry/git, unpinned `source`/`version` → malicious or changed
  code pulled at `init`. Providers unpinned or typosquatted. `terraform plan` can execute
  provider/module code — treat untrusted IaC like untrusted code.

### Kubernetes manifests (if present)
- `privileged: true`, `hostNetwork/hostPID`, no `runAsNonRoot`, no resource limits,
  secrets as env/plaintext, overly broad RBAC. See the `kubernetes` pack.

## Testing Methodology

1. Inventory IaC files, modules, providers, and the state backend.
2. Grep code + state + git history for secrets.
3. Review resources against secure defaults (public access, encryption, ingress, logging).
4. Review IAM/RBAC for wildcard and over-broad grants.
5. Check module/provider sourcing + pinning (supply chain) and state protection/locking.
6. Cross-check with `tfsec`/`checkov`; verify each flagged item against the real config.

## Validation Requirements

- Cite the exact file + resource + line and the insecure attribute (e.g. `acl = "public-read"`,
  `cidr_blocks = ["0.0.0.0/0"]`, `Action = "*"`).
- For secrets, show the leaked value's location (code/state/git) and what it unlocks — do
  not paste live secrets into the report; redact and reference.
- Explain the concrete impact (what becomes publicly reachable / what the over-broad role
  can do), not just the scanner rule id.
- This is a code review — do not apply or destroy real infrastructure.
