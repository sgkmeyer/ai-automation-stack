# Openclaw Security Audit Baseline — 2026-03-03

## Production (v2026.3.1)
**Summary: 0 critical · 1 warn · 3 info**

| Severity | Finding | Status |
|----------|---------|--------|
| WARN | `browser.remote_cdp_http` — CDP uses HTTP (172.30.0.10:9222) | Acceptable: internal Docker network only |
| INFO | `summary.attack_surface` — groups: open=0, allowlist=1; tools/hooks/browser enabled | Expected |
| INFO | `gateway.http.session_key_override_enabled` — x-openclaw-session-key accepted | Expected: trusted principals only |
| INFO | `config.secrets.hooks_token_in_config` — hooks.token in config file | Expected: file perms are 600 |

**Doctor warning:** Telegram groupPolicy=allowlist but groupAllowFrom empty — all group messages dropped. Intentional (TAR manages Telegram config).

## Dev (v2026.3.1)
**Initial summary: 2 critical · 1 warn · 3 info**

| Severity | Finding | Status |
|----------|---------|--------|
| CRITICAL | `gateway.control_ui.allowed_origins_required` — controlUi.allowedOrigins empty | **Fixed 2026-03-03** |
| CRITICAL | `fs.config.perms_world_readable` — config.json mode=644 | **Fixed 2026-03-03** (read-only mount) |
| WARN | `browser.remote_cdp_http` — CDP uses HTTP (172.31.0.10:9222) | Acceptable: internal Docker network only |
| INFO | (same 3 as production) | Expected |

## Actions Taken
- [x] Fix dev controlUi.allowedOrigins
- [x] Fix dev config.json permissions
- [x] CDP HTTP warning accepted (internal network, no fix needed)

## Post-Fix Dev Summary (2026-03-03)
**0 critical · 1 warn · 3 info**
