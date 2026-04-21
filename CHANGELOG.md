# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SECURITY.md` with private vulnerability reporting channel.
- `CONTRIBUTING.md` with issue and pull-request guidance.
- `.env.example` documenting the `OBJPRIM_*` environment variables.
- `dbbasic_object_core.config` module for runtime configuration loaded
  from the environment (mode, auth, rate limit, secret key, external
  token verification URL).
- `requirements.txt` so the README install flow works out of the box.
- `requirements-ocr.txt` for optional OCR dependencies.

### Changed
- README now links to `CONTRIBUTING.md` and `SECURITY.md`.

### Fixed
- `.gitignore` now ignores runtime pid files so fresh installs stay clean.

## [0.1.0] - Initial public release

Initial public release of the Object Primitive distributed computing
prototype. Core runtime, cluster configuration system, cluster management
tools, web app building guide, and TLDR documentation.
