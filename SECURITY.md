# Security Policy

## Supported versions

This project is pre-1.0. Only the latest released version on the default branch
receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest  | ✅        |
| older   | ❌        |

## Reporting a vulnerability

Please report vulnerabilities privately — do not open a public issue.

Use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability):
open the repository's **Security** tab and choose **Report a vulnerability**.

Include reproduction steps and affected versions. Expect an initial response
within a few days.

## Handling tokens

`SHORTCUT_API_TOKEN` is a workspace credential. Never commit it or paste it into
issues, logs, or test fixtures. The server reads it from the environment only.
