# Security Policy — AuraQA

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x (current) | ✅ Yes |

---

## Security Architecture

AuraQA implements the following security measures:

### License Protection
- **Hardware-bound license**: System generates a machine fingerprint (MAC address + hostname + architecture) and signs it with an HMAC-SHA256 signature using the MASTER_KEY
- **Startup enforcement**: Backend refuses to start if the license is missing, invalid, or from a different machine
- **Key separation**: The MASTER_KEY and `.license` file are never included in the repository

### Authentication
- **JWT tokens**: HS256-signed tokens with configurable expiry (default 60 minutes)
- **bcrypt password hashing**: All passwords are hashed with bcrypt before storage
- **Account lockout**: Accounts are locked for 15 minutes after 5 consecutive failed login attempts
- **Email enumeration protection**: Generic error messages prevent username discovery

### API Security
- **CORS restricted**: Only `http://localhost:5000` is whitelisted
- **API documentation hidden**: `/docs`, `/redoc`, and `/openapi.json` are disabled
- **Security response headers**: Every response includes `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, and `Referrer-Policy` headers
- **Specific HTTP methods only**: Only `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS` are allowed

### AI Safety
- **Prompt injection guard**: Known injection phrases are detected and blocked before reaching the AI model
- **System prompt enforcement**: A security system prompt is prepended to every AI request, instructing the model to stay within its role
- **Local inference only**: Ollama runs entirely on localhost — no data is ever sent to external services

### Data Privacy
- **Fully offline**: No external API calls are ever made during normal operation
- **Local storage only**: All documents, chat history, and user data stay on the local machine
- **Database**: SQLite stored locally, not accessible remotely

---

## Reporting a Vulnerability

If you discover a security vulnerability in AuraQA:

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Contact the author directly: **Sageer Auwal**, Federal University of Kashef
3. Provide a clear description of the vulnerability and steps to reproduce
4. Allow reasonable time for the issue to be investigated and patched

Security reports will be acknowledged within 48 hours.

---

## Out of Scope

The following are known limitations and are not considered vulnerabilities in the context of this offline academic system:

- Unencrypted SQLite database (planned for future version)
- HTTP-only communication (no HTTPS in local deployment)
- No GPU firewall (Ollama port 11434 relies on OS-level firewall rules)

---

© 2026 Sageer Auwal — AuraQA Security Policy
