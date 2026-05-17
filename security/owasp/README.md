# OWASP Security Scanning

This folder contains commands and scripts to run automated security checks aligned with OWASP-focused practices.

## Layers

1. Dependency scanning (SCA): pip-audit
2. Static code scanning (SAST): bandit, semgrep
3. Dynamic API baseline scan (DAST): OWASP ZAP baseline

## Prerequisites

- Python environment activated
- Docker installed and running (for ZAP baseline)
- API running locally for DAST (for example on http://localhost:8000)

## Install tools

Run once:

```bash
/opt/anaconda3/envs/crypto_env/bin/python -m pip install -r requirements-security.txt
```

## Run all OWASP scan layers

```bash
bash security/owasp/run_owasp_scans.sh
```

## Outputs

Timestamped output directories are created under security/reports. Expected files include:

- bandit.json
- pip-audit.json
- semgrep.json
- zap-baseline.json
- zap-baseline.html
