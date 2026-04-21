# Security Policy

## Reporting a Vulnerability

If you find a security issue in Object Primitive, please report it privately
rather than opening a public GitHub issue.

- **Email:** dan@askrobots.com
- **Project site:** https://dbbasic.com

Please include steps to reproduce, affected version or commit, and the
impact you observed. We aim to acknowledge reports within a few business
days.

## Scope

This repository hosts the Object Primitive server and its supporting
packages. Vulnerabilities in deployments you run yourself are in scope
only to the extent that they stem from a defect in this code.

## Deployment

Object Primitive ships with a development mode that relaxes auth for local
use. For anything reachable from the public internet, set
`OBJPRIM_MODE=production` and `OBJPRIM_AUTH_PASS`. See `.env.example` for
the full set of security-relevant environment variables.
