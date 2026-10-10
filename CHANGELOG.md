# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project is an Apache-2.0 fork of
[Strix](https://github.com/usestrix/strix).

## [Unreleased]

### Added
- GitHub Action (`action.yml`) — run a scan in CI with `uses: MaverickGH/ai-raider@v1`.
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, and this `CHANGELOG.md`.
- gRPC / Protobuf security knowledge pack (`airaider/skills/protocols/grpc.md`).
- DefectDojo findings export (`scripts/export-defectdojo.py`, SARIF → import-scan).
- Bilingual reports via `--report-lang` (en default, ru) across markdown, vuln cards and
  the viewer PDF; Cyrillic-safe PDF (registers a system Unicode font).
- Self-host onboarding: `setup.sh`, `env.example`, `SELF-HOST.md`.
- CI: `pytest` on pull requests and pushes to `main`.

### Changed
- Rebranded from Strix to **AI-Raider**: package `airaider/`, CLI `ai-raider`, config
  `~/.ai-raider`, env `AIRAIDER_*`.
- Documentation is English-first with Russian kept as `*.ru.md` and a language switcher.
- Telemetry off by default; the upstream managed-cloud client and its UI were removed.

### Security
- Reports keep provider keys out of the tool (entered via env/Keychain, never printed).
