---
name: spring
description: Spring Boot / Spring Framework (Java) security testing — actuators, SpEL injection, Spring Security authz gaps, deserialization, mass assignment, and known RCE chains
---

# Spring (Java)

Security testing for Spring Boot / Spring Framework apps. Java enterprise defaults leak a
lot: exposed actuators, SpEL evaluation, permissive security filter chains, and a long
history of deserialization / expression RCE. Fingerprint the stack, then hit the
Spring-specific surface before generic web tests.

## Fingerprinting

- Error pages: Whitelabel Error Page, stack traces naming `org.springframework.*`.
- Headers/cookies: `JSESSIONID`, `X-Application-Context`.
- Paths: `/actuator`, `/actuator/health`, `/error`, `/swagger-ui.html`, `/v3/api-docs`.
- Build hints: `/BOOT-INF/`, `spring-boot-starter-*` in SBOM, `favicon.ico` hash.

## Attack Surface

- **Actuator endpoints** (`/actuator/*`): health, env, beans, mappings, loggers,
  heapdump, threaddump, `httptrace`, `metrics`, and the dangerous `env`/`refresh`/
  `jolokia`/`gateway` ones.
- **SpEL** (Spring Expression Language) in `@Value`, `@PreAuthorize`, routing, Thymeleaf.
- **Spring Security** filter chain: method vs URL authorization, `permitAll`, actuator exposure.
- **Spring Cloud Gateway / Function**: routing/filter injection, `functionRouter`.
- **Data binding**: `@ModelAttribute` / `WebDataBinder` mass assignment.
- **Deserialization**: Jackson polymorphic types, JNDI, old commons-collections gadgets.

## Reconnaissance

```bash
# Actuator discovery (base path is /actuator in Boot 2+, root in Boot 1)
for e in health info env beans mappings loggers configprops httptrace heapdump threaddump metrics scheduledtasks gateway/routes jolucus; do
  curl -s -o /dev/null -w "%{http_code} /actuator/$e\n" "$TARGET/actuator/$e"; done
curl -s "$TARGET/actuator/env" | head        # property leak (credentials, keys)
curl -s "$TARGET/v3/api-docs" | head          # OpenAPI → full endpoint map
```

- `/actuator/mappings` reveals every route + handler.
- `/actuator/heapdump` downloads memory → secrets, tokens, sessions.
- `/actuator/env` leaks config; with `/actuator/refresh` + writable props, escalate.

## Key Vulnerabilities

### Exposed / sensitive actuators
- `heapdump` → extract secrets (grep the dump for `password`, `token`, `Authorization`).
- `env` → leaked credentials; POST to `env` (if `@RefreshScope`) to overwrite properties.
- `jolokia`/`logfile`/`gateway` → read files, trigger beans, or SSRF via gateway routes.
- `httptrace` → capture other users' requests incl. auth headers.

### SpEL injection
User input reaching an expression evaluator → RCE:
`T(java.lang.Runtime).getRuntime().exec(...)`. Test `@PreAuthorize` inputs, routing
expressions, Thymeleaf `${...}`/`__${...}__::`, and Spring Cloud Gateway SpEL filters.

### Spring Security authz gaps
- URL-based rules miss method-level access → call the handler directly.
- `permitAll()` on a pattern that also matches a sensitive path.
- Actuator left on the default role; `management.endpoints.web.exposure.include=*`.
- JWT/session: see `authentication_jwt`.

### Known CVE chains (confirm version first)
- **Spring4Shell** (CVE-2022-22965): `WebDataBinder` class-loader manipulation → RCE on
  Tombcat-deployed WARs with data binding.
- **Spring Cloud Function SpEL** (CVE-2022-22963): `spring.cloud.function.routing-expression` header → RCE.
- **Spring Cloud Gateway** (CVE-2022-22947): actuator `gateway` SpEL → RCE.
- Jackson / commons-collections deserialization gadgets when polymorphic typing is on.

### Mass assignment
`@ModelAttribute` binds request params to the whole object → set fields like `role`,
`isAdmin`, `accountId` the form never exposed. See `mass_assignment`.

## Testing Methodology

1. Fingerprint Spring + version (error page, actuator, deps).
2. Enumerate actuators; pull `env`/`mappings`/`heapdump` for secrets and the route map.
3. From `mappings`/OpenAPI, test each handler for authz (method-level vs URL rules).
4. Probe SpEL sinks (routing, `@Value`, Thymeleaf, gateway filters).
5. Check data binding for mass assignment.
6. Match the exact version against known SpEL/deserialization CVE chains before firing.

## Validation Requirements

- Prove actuator exposure with the leaked data (a secret from `heapdump`/`env`, the full
  `mappings` list) — not just a 200.
- For SpEL/RCE, show command output or an out-of-band callback from a benign payload.
- For authz bypass, show the handler succeeding without the required role.
- Never run destructive commands on production; demonstrate RCE with a safe proof (e.g.
  `id`, a DNS callback).
