---
marp: true
theme: default
paginate: false
style: |
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@300;400;600;800&display=swap');
  section {
    font-family: 'Noto Sans', sans-serif;
    color: #c8d4e0;
    background: #0f1729;
    padding: 50px 70px;
    font-size: 22px;
  }
  h1 {
    color: #ffffff;
    font-weight: 800;
    font-size: 1.8em;
    letter-spacing: -1px;
    margin-bottom: 12px;
  }
  h2 {
    color: #14A89B;
    font-weight: 700;
    font-size: 1.5em;
    margin-bottom: 10px;
  }
  strong {
    color: #14A89B;
  }
  em {
    color: #8899aa;
    font-style: normal;
  }
  code {
    background: #1a2540;
    color: #14A89B;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 0.85em;
    font-family: 'JetBrains Mono', monospace;
  }
  ul, ol {
    font-size: 0.95em;
    line-height: 1.6;
  }
  li {
    margin-bottom: 4px;
  }
  section.lead {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
  section.lead h1 {
    font-size: 2.4em;
    margin-bottom: 4px;
  }
  section.lead p {
    color: #8899aa;
    font-size: 0.95em;
    margin: 4px 0;
  }
  table {
    font-size: 0.85em;
    border-collapse: collapse;
    width: 100%;
  }
  th {
    background: #14A89B20;
    color: #14A89B;
    padding: 8px 12px;
    text-align: left;
  }
  td {
    padding: 6px 12px;
    border-bottom: 1px solid #1a2540;
  }
---

<!-- _class: lead -->

![w:120](../public/logo.png)

# amanat

**Data Governance AI Agent**

*Scans cloud services for sensitive data. Detects, evaluates, remediates. Runs locally.*

Adam Munawar Rahman · Auth0 "Authorized to Act" Hackathon 2026

---

## The Problem

830,000 Rohingya refugees had biometric data shared with Myanmar without consent (HRW, 2021).

- GBV reports sit on OneDrive with "anyone with the link" access
- Case numbers and medical details posted in public Slack channels
- Biometric enrollment logs stored on unencrypted field laptops
- The ICRC published a 400-page handbook. The IASC published guidance. **No tool enforces them.**

---

## Amanat

**Auth0 Token Vault** connects OneDrive, Slack, Outlook with per-service OAuth scoping.

**CIBA step-up auth** sends Guardian push notifications for destructive actions (revoke, delete). User approves on their phone before the agent proceeds.

**Hybrid PII detection** (regex + Granite 4 Micro) catches names in any script, implicit identifiers, structural patterns.

**Policy RAG** grounds analysis in 1,059 chunks from real ICRC/IASC/GDPR/Sphere PDFs via BM25 retrieval.

**All local.** IBM Granite 4 Micro via llama-server. Beneficiary data never leaves the machine.

---

<!-- _class: lead -->

# Demo

---

<!-- _class: lead -->

![w:100](../public/logo.png)

# Thank You!

adamr.io · linkedin.com/in/adamsrahman · github.com/msradam

*Adam Munawar Rahman*
