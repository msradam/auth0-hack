# Humanitarian Data Protection & Governance: Real Incidents, Pain Points, and Workflows

Research compiled March 2026 for Amanat hackathon project.

---

## 1. Real Data Breaches and Incidents

### 1.1 ICRC Cyberattack (2022) -- The Big One

**What happened:** On November 9, 2021, state-sponsored hackers breached servers hosting the ICRC's Restoring Family Links program. The breach wasn't detected until January 18, 2022 -- 70 days later.

**Scale:** 515,000+ records of highly vulnerable people -- missing persons, separated families, detainees -- from at least 60 Red Cross and Red Crescent National Societies worldwide.

**Data exposed:** Names, locations, contact information, health records, personal identification documents, family relationships, and details of individuals' circumstances related to separation and family search.

**How they got in:** Exploited an unpatched critical vulnerability (CVE-2021-40539) in an authentication module. Used web shells, compromised admin credentials, moved laterally through the network, exfiltrated registry and domain files. The malware was "specifically crafted to bypass [ICRC's] anti-malware solutions" -- advanced persistent threat tools not publicly available.

**Impact:** ICRC had to shut down Restoring Family Links systems entirely, directly affecting the Movement's ability to reunite separated families. The very people who needed the ICRC most -- people in conflict zones looking for missing relatives -- were cut off from services.

**Response:** ICRC called on states to "protect humanitarian organizations online as they do offline." Deployed two-factor authentication, external penetration testing, advanced endpoint detection.

**Why this matters for Amanat:** This is the canonical example. A state actor specifically targeted the most sensitive humanitarian data imaginable. The 70-day detection gap shows that even the ICRC -- arguably the most data-protection-conscious humanitarian org -- had inadequate monitoring.

Sources:
- [ICRC: Cyber-attack on ICRC -- What We Know](https://www.icrc.org/en/document/cyber-attack-icrc-what-we-know)
- [ICRC: Sophisticated cyber-attack targets Red Cross Red Crescent data](https://www.icrc.org/en/document/sophisticated-cyber-attack-targets-red-cross-red-crescent-data-500000-people)
- [Red Cross data breach - Wikipedia](https://en.wikipedia.org/wiki/Red_Cross_data_breach)
- [NPR: Cyberattack on Red Cross compromised sensitive data](https://www.npr.org/2022/01/20/1074405423/red-cross-cyberattack)
- [Computer Weekly: Red Cross cyber attack the work of nation-state actors](https://www.computerweekly.com/news/252513537/Red-Cross-cyber-attack-the-work-of-nation-state-actors)

---

### 1.2 UNHCR Rohingya Biometric Data Sharing

**What happened:** UNHCR collected biometric data (fingerprints, iris scans, facial images) from Rohingya refugees in Bangladesh as part of a joint registration exercise. This data was subsequently shared with the government of Bangladesh, which then shared it with Myanmar -- the very country the Rohingya had fled from.

**Scale:** At least 830,000 names of Rohingya refugees submitted to Myanmar between 2018-2021, along with biometric and other personal data.

**The consent failure:** Refugees were told to register to receive aid. The risks of sharing their biometrics were not discussed. The possibility of data being shared with Myanmar was not mentioned. UNHCR did not carry out a Data Protection Impact Assessment, breaching its own policies. HRW's 2021 investigation concluded UNHCR "shared Rohingya data without informed consent."

**Consequences for refugees:** When they learned their data had been shared and their names appeared on verified repatriation lists, refugees went into hiding. The fundamental trust between UNHCR and the population it serves was broken.

**2025 escalation:** 300-400 Rohingya refugee families in Nayapara and Kutupalong camps were cut off from food aid and essential services after refusing to participate in a new biometric data collection drive. No fingerprint, no food.

**Why this matters for Amanat:** This is the clearest example of the "consent paradox" in humanitarian settings. When acceptance of biometric registration is a prerequisite for life-saving food and medical treatment, consent cannot be freely given. This is not an edge case -- it's the fundamental structural problem.

Sources:
- [HRW: UN Shared Rohingya Data Without Informed Consent](https://www.hrw.org/news/2021/06/15/un-shared-rohingya-data-without-informed-consent)
- [ODI: Although Shocking, the Rohingya Biometrics Scandal Is Not Surprising](https://odi.org/en/insights/although-shocking-the-rohingya-biometrics-scandal-is-not-surprising-and-could-have-been-prevented/)
- [The New Humanitarian: Rohingya data protection and the UN's betrayal](https://www.thenewhumanitarian.org/opinion/2021/6/21/rohingya-data-protection-and-UN-betrayal)
- [The Diplomat: No Fingerprint, No Food](https://thediplomat.com/2025/06/no-fingerprint-no-food-how-the-un-is-failing-the-rohingya/)
- [The Diplomat: UNHCR Defends Biometric Enrollment Push](https://thediplomat.com/2025/06/unhcr-defends-biometric-enrollment-push-for-rohingya-refugees/)

---

### 1.3 WFP SCOPE System and Data Handling Failures

**The system:** WFP's SCOPE is a central web-based beneficiary and transfer management system holding records on 26 million people, 5.8 million of which include fingerprints or photos. Used to issue ration cards for accessing cash, vouchers, and in-kind assistance.

**The 2017 audit findings:** An internal WFP audit (November 2017) found a "litany of data protection failings":
- Beneficiaries did not give informed consent to the use of personal data
- Data was routinely copied without encryption or password protection
- System needed "major improvement" in governance and risk management
- An NGO manager stated the SCOPE database "failed the test of data protection by design and default"

**The Palantir deal (2019):** WFP signed a $45 million, five-year partnership with Palantir Technologies -- a company with deep ties to US intelligence services and known for facilitating ICE operations. Over 80 organizations and individuals signed an open letter opposing the deal, raising concerns about:
- De-anonymization through the "mosaic effect" when merging large datasets
- Algorithmic bias in fraud detection models
- Vendor lock-in and spiraling costs
- Lack of accountability since it's unclear if GDPR applies to UN agencies
- No international treaties covering data privacy for UN operations

**The Yemen biometrics conflict:** WFP clashed with Houthi authorities who argued WFP was violating national laws by maintaining control over biometric data storage.

**Why this matters for Amanat:** WFP demonstrates the full spectrum of data governance failures: poor technical controls, inadequate consent, partnership with surveillance-adjacent firms, and cross-border jurisdictional conflicts. The Palantir deal shows how humanitarian data can flow to entities with fundamentally different values.

Sources:
- [The New Humanitarian: Audit exposes UN food agency's poor data-handling](https://www.thenewhumanitarian.org/news/2018/01/18/exclusive-audit-exposes-un-food-agency-s-poor-data-handling)
- [Privacy International: WFP signed a deal with CIA-backed Palantir](https://privacyinternational.org/news-analysis/2712/one-uns-largest-aid-programmes-just-signed-deal-cia-backed-data-monolith)
- [Devex: WFP and Palantir controversy should be a wake-up call](https://www.devex.com/news/opinion-the-wfp-and-palantir-controversy-should-be-a-wake-up-call-for-humanitarian-community-94307)
- [Responsible Data: Open Letter to WFP re Palantir](https://responsibledata.io/2019/02/08/open-letter-to-wfp-re-palantir-agreement/)

---

### 1.4 Blackbaud Ransomware Attack (2020)

**What happened:** A major ransomware attack on Blackbaud, a cloud-based fundraising platform used by hundreds of nonprofits. Hackers had access from February to May 2020. Blackbaud paid an undisclosed ransom.

**Scale:** 536 organizations, close to 13 million people affected.

**NGOs hit:** World Vision, Save the Children, Human Rights Watch, CARE Canada, and dozens more.

**Data exposed:** Names, addresses, donation records, event participation, giving history, biographical details including dates of birth.

**Why it matters:** Even when NGOs have decent internal data practices, their third-party vendors can be single points of failure. The Blackbaud breach showed the supply chain risk -- humanitarian orgs don't just need to protect their own systems, they need to audit every vendor touching donor and beneficiary data.

**Legal outcome:** Blackbaud was charged by the SEC for misleading disclosures and settled for $49.5 million with US states.

Sources:
- [The New Humanitarian: Donor details hacked in NGO data breach](https://www.thenewhumanitarian.org/news/2020/08/04/NGO-fundraising-database-hack)
- [Save the Children: Statement on Blackbaud Security Breach](https://www.savethechildren.org/us/about-us/media-and-news/2020-press-releases/save-the-children-statement-on-blackbaud-security-breach)
- [ITRC: Blackbaud Data Breach Leaves Lasting Impact](https://www.idtheftcenter.org/post/blackbaud-data-breach-leaves-lasting-impact-on-u-s-and-international-nonprofits/)

---

### 1.5 Save the Children -- Separate Cyberattack

Save the Children International was also hit by a separate cyberattack (beyond Blackbaud), though the organization claimed operations weren't impacted.

Source: [The Record: Save the Children hit with cyberattack](https://therecord.media/save-the-children-charity-cyberattack)

---

### 1.6 Oxfam and MSF -- Gaza Staff Data Demands (2025-2026)

**What happened:** Israel demanded personal data of Palestinian staff from humanitarian organizations operating in Gaza. Oxfam refused, stating: "We will not transfer sensitive personal data to a party to the conflict since this would breach humanitarian principles, duty of care and data protection obligations." MSF also refused.

**Why this matters:** This is a live example of a state actor demanding humanitarian staff data, and organizations having to choose between data protection principles and operational access. It demonstrates that data governance isn't just about preventing breaches -- it's about having the policies and backbone to refuse data demands from powerful actors.

Sources:
- [Al Jazeera: Oxfam refuses to provide Israel with details of Palestinian staff](https://www.aljazeera.com/news/2026/1/28/oxfam-refuses-to-provide-israel-with-details-of-staff-in-gaza)
- [Al Jazeera: MSF says it will not hand over staff details to Israeli authorities](https://www.aljazeera.com/news/2026/1/30/msf-says-it-will-not-hand-over-staff-details-to-israeli-authorities)

---

### 1.7 Broader Cybersecurity Threat Landscape

**Key statistics:**
- Nonprofits were the **second-most targeted sector** per Okta's 2025 report
- Microsoft's Digital Defense Report 2024: nonprofits are the **fourth most targeted by nation-state actors**
- Cloudflare Project Galileo: **241% increase in cyberattacks** on civil society between 2024 and 2025
- Human rights and civil society organizations are the **second most impacted by DDoS attacks**
- CyberPeace Institute documented **44 targeted attacks** against NGOs including ransomware, DDoS, defacement, fraud, spyware, and data leaks

Sources:
- [NetHope: 2025 State of Humanitarian and Development Cybersecurity Report](https://nethope.org/toolkits/2025-state-of-humanitarian-and-development-cybersecurity-report/)
- [CyberPeace Institute: NGOs at Risk](https://geneva.cyberpeace.ngo/)
- [CyberPeace Institute: Submission on Protection of Humanitarian Sector](https://cyberpeaceinstitute.org/news/submission-on-the-protection-of-the-humanitarian-sector-2/)

---

## 2. What Tools Do NGOs Actually Use?

### 2.1 Data Collection

| Tool | Used By | Notes |
|------|---------|-------|
| **KoBoToolbox** | ~14,000+ organizations, 20M+ surveys/month | Dominant in humanitarian emergencies. OCHA-backed. Open source, offline-capable. |
| **ODK (Open Data Kit)** | Foundation for KoBo and many others | Open source mobile data collection. KoBoCollect is based on ODK Collect. |
| **SurveyCTO** | Research-heavy orgs, evaluations | Integrates with Google Sheets, SPSS, Stata. Commercial. |
| **CommCare (Dimagi)** | Health-focused programs | Case management + data collection. Used in 80+ countries. |

### 2.2 Case Management Systems

| Tool | Used By | Purpose |
|------|---------|---------|
| **Primero** | UNICEF, child protection actors | Protection case management (GBV, child protection). Offline-capable PWA. |
| **ProGres (PRIMES)** | UNHCR | Refugee registration and case management. Role-based access. Holds biometric data. |
| **GBVIMS** | GBV actors globally | Gender-Based Violence Information Management System. Standardized incident data. |
| **ActivityInfo** | Humanitarian clusters, M&E teams | Activity tracking and reporting. Multi-script font support. |

### 2.3 Communication and Collaboration

| Tool | Usage Pattern | Data Protection Risk |
|------|--------------|---------------------|
| **WhatsApp** | Ubiquitous for field comms, beneficiary contact, inter-agency coordination | PII shared in chats, group messages, no org control over data retention. E2E encrypted but metadata exposed. |
| **Microsoft Teams + SharePoint** | HQ-level collaboration, document management | Organizations already on Microsoft stack integrate naturally. SharePoint for document storage. |
| **Google Workspace** | Common in smaller NGOs, some large orgs | Google Sheets widely used for beneficiary tracking (concerning). |
| **Slack** | Inter-agency coordination, tech-savvy orgs | Used for department/volunteer coordination. |
| **Email** | Universal | Often used to send beneficiary lists as unencrypted attachments. |

### 2.4 The Shadow IT Problem

- 93% of aid workers use or have tried AI tools
- 70% incorporate them into daily workflows
- 69% rely on commercial platforms (ChatGPT, Claude) rather than purpose-built humanitarian solutions
- Workers adopt "shadow" tools to fill gaps their organizations don't address
- Only 21% of organizations have established governance frameworks

This means beneficiary data is flowing through ChatGPT, personal WhatsApp accounts, personal Google Drives, and tools the organization hasn't vetted or approved.

Sources:
- [Humanitarian Leadership Academy: Shadow AI Study](https://www.humanitarianleadershipacademy.org/news/global-study-highlights-shadow-ai-as-humanitarian-workers-outpace-organizations-in-technology-adoption/)
- [UNHCR Innovation: Meeting communities where they are -- messaging apps](https://medium.com/unhcr-innovation-service/meeting-communities-where-they-are-the-increasing-preference-of-messaging-apps-3338ee9ee957)
- [Access Now: Mapping Humanitarian Tech](https://www.accessnow.org/wp-content/uploads/2024/02/Mapping-humanitarian-tech-February-2024.pdf)

---

## 3. Specific Pain Points -- Where Data Governance Fails in Practice

### 3.1 The WhatsApp Problem

Field workers use personal WhatsApp accounts to:
- Share beneficiary lists for distribution coordination
- Send case referrals between organizations
- Communicate with beneficiaries about GBV incidents or protection concerns
- Share photos of documents, assessments, registration forms

**Why it happens:** WhatsApp is already installed on everyone's phone, works in low-bandwidth settings, and 2+ billion people use it. Beneficiaries prefer it. It's "meeting communities where they are."

**Why it's dangerous:** Organization has zero control over data retention. Messages live on personal devices. Staff leave the organization and retain all historical chats. Metadata (who contacted whom, when, how often) is accessible to WhatsApp/Meta. Phone numbers are PII. Group chats can leak to unintended recipients.

The ICRC Handbook on Data Protection in Humanitarian Action dedicates an entire chapter (Chapter 12) to mobile messaging apps, recognizing this as a sector-wide problem.

### 3.2 Cloud Storage Oversharing

**Documented incident:** A security researcher found an administrative dashboard for an aid agency's beneficiary management system left publicly accessible, giving "full control to view and edit financial and personal details and download data from a system containing financial records totalling about $4 million."

**Common patterns:**
- Beneficiary databases stored in shared Google Sheets with org-wide access
- Case files on shared drives accessible to all staff, not just protection workers
- Documents shared via links that don't expire
- No systematic review of access permissions when staff change roles or leave
- Legacy program data left on drives indefinitely after programs close

### 3.3 PII in Donor Reports

Donors increasingly request:
- Disaggregated data (gender, age, disability markers)
- Household-level survey results
- Individual case studies with identifying details
- Program-level data that, when combined, can re-identify individuals

**The re-identification risk:** What appears to be non-personal data can allow re-identification "when data can be traced back or linked to an individual(s) or group(s) because it is not adequately anonymized." A beneficiary list disaggregated by village, gender, age, and disability status may identify a single person in a small community.

The Centre for Humanitarian Data has published specific guidance on responsible data sharing with donors, but adoption is inconsistent.

Sources:
- [Centre for Humanitarian Data: Responsible Data Sharing with Donors](https://centre.humdata.org/guidance-note-responsible-data-sharing-with-donors/)
- [GPPi: Risks Associated With Humanitarian Data Sharing With Donors](https://gppi.net/2021/09/06/data-sharing-with-humanitarian-donors)

### 3.4 Biometric Enrollment Without Proper Consent

The structural problem: when humanitarian aid is conditional on biometric enrollment, consent cannot be freely given. Scholars argue "free consent may require not only the absence of constraint, but also the presence of enabling conditions including basic material support."

**Real-world pattern:**
1. Organization sets up registration point
2. Refugees are told to register to access food/shelter/healthcare
3. Registration includes biometric capture (fingerprints, iris scans, photos)
4. Consent forms (if they exist) are in languages refugees may not fully understand
5. Refugees sign because the alternative is no aid
6. Data is stored in systems they have no visibility into
7. Data may later be shared with governments, other agencies, or commercial partners

### 3.5 GBV Data Confidentiality Failures

GBV (gender-based violence) case data is the most sensitive category in humanitarian work. Failure to protect it can result in:
- Reprisal attacks by perpetrators
- Stigma and ostracism from families and communities
- Physical danger to survivors

**Specific risks documented:**
- Remote GBV service delivery (phone/SMS) creates eavesdropping risks
- Case files stored on shared drives accessible to non-protection staff
- Hard copies of GBV case files kept in practitioners' homes during COVID-era remote work
- Lack of differentiated access rights -- all staff seeing all case data
- GBV incident data accessible to people who don't need it

**Standard failures:**
- No codes or red flag phrases for phone consultations
- Data protection clauses missing from staff contracts
- No separation between GBV case management data and general program data

Sources:
- [Inter-Agency GBV Case Management Guidelines 2017](https://gbvresponders.org/wp-content/uploads/2017/04/Interagency-GBV-Case-Management-Guidelines_Final_2017_Low-Res.pdf)
- [UNHCR GBV Toolkit: Information Management](https://www.unhcr.org/gbv-toolkit/information-management/)
- [ReliefWeb: Documentation of survivors of GBV](https://reliefweb.int/report/world/documentation-survivors-gender-based-violence-gbv)

### 3.6 Data Retention -- The Problem Nobody Addresses

**What should happen:** When a program ends, beneficiary data collected for that program should be reviewed and, where there's no ongoing purpose, deleted.

**What actually happens:** Data persists indefinitely. Programs end, staff rotate, and nobody takes responsibility for cleaning up. Old beneficiary databases sit on servers, shared drives, and backup tapes for years.

**Why it's dangerous:**
- Stale data can be breached years later (see ICRC -- the data was from programs across 60+ national societies)
- Political situations change -- data that was safe to hold under one government becomes dangerous under another
- No systematic retention policies in most humanitarian organizations
- Deletion is seen as risky ("what if we need it later?") rather than retention being seen as risky

### 3.7 The Consent Paradox in Humanitarian Settings

Meaningful informed consent requires:
- Understanding what data is being collected
- Understanding how it will be used
- Freedom to say no without consequences
- Ability to withdraw consent later

In humanitarian settings, none of these conditions are reliably met:
- **Language barriers:** Consent forms in languages beneficiaries don't fully understand
- **Power imbalance:** "The voluntariness of consent can be questioned in many migration contexts due to extreme power asymmetries"
- **Aid conditionality:** Refusal of data collection = refusal of aid in practice
- **Cultural context:** Written consent forms are alien to many communities
- **Time pressure:** Registration during acute emergencies doesn't allow meaningful consent processes
- **Ongoing consent:** One-time consent at registration doesn't cover evolving data uses

Sources:
- [PMC: Scoping review of informed consent in humanitarian emergencies](https://pmc.ncbi.nlm.nih.gov/articles/PMC11577743/)
- [Responsible Data: Re-Imagining Informed Consent](https://responsibledata.io/anniversary/re-imagining-a-responsible-approach-to-informed-consent/)
- [LSE: Biometric refugee registration -- benefits, risks and ethics](https://blogs.lse.ac.uk/internationaldevelopment/2019/07/18/biometric-refugee-registration-between-benefits-risks-and-ethics/)

### 3.8 Cross-Border Data Transfer Nightmares

Humanitarian organizations operate across dozens of countries with conflicting data protection regimes:
- **Data localization laws:** Some countries require data to be stored locally (Yemen-WFP conflict over biometric data control)
- **Government access demands:** Host governments may demand access to beneficiary data (Bangladesh-Myanmar, Israel-Gaza)
- **GDPR extraterritoriality:** European-headquartered NGOs must comply with GDPR even for operations in Syria, DRC, etc.
- **No international humanitarian data treaty:** Unlike physical humanitarian law (Geneva Conventions), there is no equivalent for digital humanitarian data
- **Cloud hosting questions:** Where is data physically stored? Which jurisdiction governs it? Most NGOs can't answer this.

### 3.9 The Missing Policies Problem

**Privacy International found:** Major organizations including Oxfam, Save the Children, CARE, and Action Against Hunger lacked explicit policies around protecting beneficiary data, despite collecting "vast amounts of personal information" including names, locations, and detailed medical information.

**Ada Lovelace Institute:** "The data of the most vulnerable people is the least protected."

Sources:
- [Privacy International: A paucity of privacy](https://privacyinternational.org/blog/1414/paucity-privacy-humanitarian-development-organisations-need-beneficiary-data-protection)
- [Ada Lovelace Institute: Data of the most vulnerable is least protected](https://www.adalovelaceinstitute.org/blog/data-most-vulnerable-people-least-protected/)

---

## 4. Compliance Frameworks That Matter

### 4.1 GDPR

**Who's subject to it:** Any humanitarian organization established in the EU, or processing data of people in the EU, or receiving EU funding (ECHO/DG ECHO). This covers most major international NGOs headquartered in Europe: MSF (Amsterdam), Oxfam (Oxford/Nairobi), Save the Children (London), IRC (New York but EU operations), Norwegian Refugee Council (Oslo), Danish Refugee Council (Copenhagen), etc.

**Challenge for NGOs:** GDPR compliance is becoming "a hard condition for carrying out work for European donors." Many NGOs "lack expertise in data protection law and struggle to comply." Literature on GDPR compliance for NGOs is scarce compared to business organizations.

**Key tension:** GDPR requires explicit consent and data minimization, but humanitarian action sometimes requires collecting extensive personal data quickly during emergencies.

Sources:
- [IAPP: EU GDPR applicability to international organizations](https://iapp.org/news/a/eu-gdpr-applicability-to-international-organizations)
- [TechGDPR: GDPR Compliance for NGOs](https://techgdpr.com/industries/gdpr-compliance-for-ngos-and-social-enterprises/)
- [Springer: Data to the rescue -- how humanitarian aid NGOs should collect based on GDPR](https://jhumanitarianaction.springeropen.com/articles/10.1186/s41018-020-00078-0)

### 4.2 ICRC Handbook on Data Protection in Humanitarian Action

The definitive reference. Published by ICRC and Brussels Privacy Hub. Now in its second edition. Covers:
- Data protection principles applied to humanitarian contexts
- Biometrics, drones, cash transfers, cloud computing, messaging apps (each with dedicated chapters)
- Data Protection Impact Assessments (DPIAs) for humanitarian settings
- New technologies and their impact on beneficiary data

Key feature: Written by and for humanitarian organizations, not adapted from corporate compliance frameworks.

Sources:
- [ICRC: Handbook on Data Protection in Humanitarian Action](https://www.icrc.org/en/data-protection-humanitarian-action-handbook)
- [Cambridge University Press: Handbook (Second Edition)](https://www.cambridge.org/core/books/handbook-on-data-protection-in-humanitarian-action/025CE3DFD1FAD908DD1412C20E49F955)

### 4.3 IASC Operational Guidance on Data Responsibility (2023)

**What it is:** First system-wide operational guidance on data responsibility, endorsed March 2023. Developed through consultation with 250+ stakeholders.

**Key definition:** "Data responsibility in humanitarian action is the safe, ethical and effective management of personal and non-personal data for operational response."

**Adoption:** Since 2021 endorsement of the first version, humanitarians in 21 countries with Humanitarian Response Plans have adopted one or more actions, with Information Sharing Protocols being the most common.

**Governance:** Co-chaired by Danish Refugee Council, IOM, OCHA, and UNHCR. Reviewed and updated every two years.

Source: [IASC: Operational Guidance on Data Responsibility](https://interagencystandingcommittee.org/operational-response/iasc-operational-guidance-data-responsibility-humanitarian-action)

### 4.4 OCHA Data Responsibility Guidelines (2025)

Updated January 2025 to align with UN Secretariat policy and IASC guidance. Focused on OCHA staff across coordination, advocacy, policy, humanitarian financing, and information management functions. Links to the Centre for Humanitarian Data for implementation support.

Source: [OCHA: Data Responsibility Guidelines 2025](https://centre.humdata.org/data-responsibility-guidelines-2025/)

### 4.5 Core Humanitarian Standard (CHS) -- 2024 Edition

The CHS sets nine commitments for principled, accountable humanitarian action. Updated March 2024 through a two-year global consultation with 4,000+ contributors from 90+ countries. Includes a Verification Scheme with four options: self-assessment, peer review, independent verification, and certification.

While not specifically a data protection framework, CHS Commitment 4 (on communication and information) and Commitment 3 (on targeting and non-discrimination) have data governance implications.

Source: [CHS 2024](https://www.corehumanitarianstandard.org/the-standard)

### 4.6 Sphere Standards

The most widely recognized humanitarian standards globally (since 1997). Cover minimum standards in WASH, food security, shelter, and health. While not data-specific, the Protection Principles embedded in Sphere require that humanitarian actors avoid exposing people to further harm -- which includes harm from data mishandling.

Source: [Sphere Handbook](https://spherestandards.org/handbook/)

### 4.7 Donor-Specific Requirements

| Donor | Key Requirements |
|-------|-----------------|
| **USAID** | PII cannot be included in publicly available data submissions (Development Data Library). Gender/age/disability disaggregation required. |
| **ECHO (EU)** | GDPR compliance required. Standard indicators must be reported. |
| **DFID/FCDO** | Data protection requirements embedded in grant agreements. |
| **All major donors** | Increasingly requiring disaggregated beneficiary data for accountability -- creating tension with data minimization principles. |

### 4.8 National Laws in Operating Countries

This is the patchwork nightmare. Every country where an NGO operates may have different data protection laws:
- **Kenya:** Data Protection Act 2019
- **Bangladesh:** Draft Digital Security Act (used to demand data from NGOs)
- **Yemen:** Houthi authorities demanding control of biometric data
- **EU member states:** Each with GDPR implementation variations
- **Many conflict-affected countries:** Either no data protection law or laws designed for state surveillance

---

## 5. Existing Data Governance Solutions and Gaps

### 5.1 What Exists Today

**Training and certification:**
- ICRC + Maastricht University DPO Certification Programme: One-week in-person training. Conducted 8 times across 4 continents. 230+ humanitarian professionals trained (100+ sponsored by National Societies). Partners: ICRC, IFRC, UNHCR, IOM, WFP.
- This is the gold standard -- but 230 trained DPOs for an entire global sector of hundreds of thousands of workers is a drop in the ocean.

**Organizational DPO infrastructure:**
- IFRC: Has a Data Protection Office working across its global network
- UNHCR: Has a Chief Data Protection Officer providing independent oversight
- ICRC: Has its own Data Protection Framework and dedicated office
- IOM: Has a data protection function

**But:** Most medium and small NGOs have no DPO at all. The role is often added to an existing staff member's responsibilities as an afterthought.

### 5.2 DPIA Processes -- Mostly Manual

Data Protection Impact Assessments in humanitarian settings are:
- Required by ICRC handbook before new systems, projects, or data-sharing arrangements
- Supposed to involve the organization's DPO
- Expected to identify, evaluate, and address risks to data subjects
- Required when data collection is "large, repeated, or structural"

**In practice:** DPIAs are paper-based, manual processes. There is no widely-adopted automated tool for humanitarian DPIAs. Organizations that do them use Word documents and spreadsheets. Many organizations skip them entirely (UNHCR's own Rohingya data sharing lacked a DPIA despite their own policy requiring one).

Sources:
- [UNHCR: Data Protection Impact Assessment](https://www.unhcr.org/handbooks/informationintegrity/practical-tools/situation-analysis/data-protection-and-privacy/data-protection-impact-assessment)
- [Cambridge: DPIAs in Handbook on Data Protection in Humanitarian Action](https://www.cambridge.org/core/books/handbook-on-data-protection-in-humanitarian-action/data-protection-impact-assessments-dpias/1CBF38765A1D67976FD11BB8BB468458)

### 5.3 What's Missing -- The Amanat Opportunity

**There is no tool that does what we're building.** Specifically, there is no:

1. **Automated data governance agent** that can scan an organization's actual cloud storage, messaging, and collaboration tools to identify data protection risks in real time

2. **Automated DPIA tool** designed for humanitarian contexts (the closest is generic GDPR DPIA templates that don't account for humanitarian-specific risks like the consent paradox or conflict-zone data handling)

3. **Cross-platform visibility tool** that shows where beneficiary data actually lives across SharePoint, Google Drive, WhatsApp, KoBo exports, email attachments, etc.

4. **Intelligent retention management** that identifies stale beneficiary data and flags it for review/deletion

5. **Donor reporting scrubber** that can check reports for re-identification risks before submission

6. **Access audit tool** that maps who has access to sensitive data (especially GBV case files) and flags inappropriate access patterns

**What exists in the commercial space** (but not tailored to humanitarian):
- OneTrust, TrustArc, BigID -- enterprise privacy management tools, priced for Fortune 500, not NGOs
- Microsoft Purview -- data governance for Microsoft ecosystem, but no humanitarian-specific classification
- Google DLP -- scans for PII patterns but doesn't understand humanitarian data categories

---

## 6. Killer Use Cases for the Pitch

These are real, documented scenarios that happen every day in humanitarian operations:

### 6.1 "The WhatsApp Distribution List"
A field worker needs to coordinate food distribution across three sites. They share a beneficiary list (names, locations, family sizes, vulnerability scores) via WhatsApp to colleagues, local partners, and a government liaison. The list now lives on 15 personal phones, with no organizational control, no deletion pathway, and potential government access.

### 6.2 "The Orphaned Case Files"
A child protection program in eastern DRC closes after three years of funding. The case files -- containing names, ages, family situations, abuse histories, and locations of hundreds of children -- remain on a shared Google Drive. The project manager has moved to a new organization. Their replacement has never seen these files. They sit there for years.

### 6.3 "The Donor Report with Re-identification Risk"
A program manager prepares a final report for ECHO funding. It includes a table: beneficiary disaggregation by village, gender, age bracket, and disability status. In a village of 200 people, there is one disabled woman aged 50-60. She is now identified. The report is published on ECHO's transparency portal.

### 6.4 "The Biometric Registration Line"
A new influx of refugees arrives at a camp. Registration must happen fast to get people fed and sheltered. Biometric enrollment happens in an open tent with a queue of 200 people. "Consent" is a checkbox on a tablet, explained in a language most refugees partially understand. The data feeds into a system that multiple agencies access. Two years later, the host government requests access for "repatriation planning."

### 6.5 "The GBV Case Worker's Laptop"
A GBV case worker stores case notes on their personal laptop because the organization's server is unreliable in the field location. The laptop has no full-disk encryption. The case worker travels between sites on public transport. Each case file contains the survivor's name, location, details of sexual violence, and the alleged perpetrator's identity (who may be a community leader or armed group member).

### 6.6 "The AI-Assisted Assessment"
A field coordinator uses ChatGPT to help analyze a needs assessment survey. They paste 500 rows of household data -- including GPS coordinates, family compositions, and vulnerability scores -- into the prompt. The data is now in OpenAI's systems. Nobody in the organization knows this happened.

---

## 7. Mapping the Humanitarian Data Ecosystem

```
Beneficiary Contact Points          Organizational Systems              External Recipients
==========================          ======================              ===================

Registration (KoBo/ODK) ---------> Case Management (Primero/ProGres)   Donors (USAID/ECHO/DFID)
                                           |                                    |
Biometric Enrollment (SCOPE) ----->  Cloud Storage (SharePoint/GDrive)  Host Governments
                                           |                                    |
Field Interviews -----------------> Email/Attachments                   Partner NGOs
                                           |                                    |
Phone/SMS/WhatsApp Comms --------> Messaging (WhatsApp/Teams/Slack)    Commercial Partners
                                           |                                    |
Feedback Mechanisms --------------> Analytics (Excel/Power BI/AI)       Research Institutions
                                           |
                                    Backup/Archive
                                           |
                                    [NOBODY MONITORING ANY OF THIS]
```

---

## 8. Key Quotes for the Pitch

> "Gaps in legal and ethical frameworks for humanitarian operations and a lack of professional skills in digital data amount to a disaster waiting to happen." -- Privacy International

> "The data of the most vulnerable people is the least protected." -- Ada Lovelace Institute

> "We will not transfer sensitive personal data to a party to the conflict since this would breach humanitarian principles, duty of care and data protection obligations." -- Oxfam (2026, regarding Gaza staff data)

> "The implementation of data responsibility in practice is often inconsistent within and across humanitarian response contexts." -- IASC Operational Guidance

> "No fingerprint, no food." -- The Diplomat (2025, on Rohingya biometric enrollment)

> "Unintended mistakes from simple negligence, inattention, or lack of training were more frequently happening than intentional threats." -- CHA Berlin

---

## 9. Summary: Why Amanat Fills a Real Gap

The humanitarian sector has:
- **Frameworks:** ICRC Handbook, IASC Guidance, OCHA Guidelines, CHS, GDPR
- **Some training:** 230 DPOs certified in 8 training sessions over several years
- **Good intentions:** Most organizations know data protection matters

The humanitarian sector lacks:
- **Automation:** DPIAs are Word documents. Access reviews are manual. Retention is unmanaged.
- **Visibility:** Nobody can answer "where is our beneficiary data right now?" across all systems
- **Real-time monitoring:** The ICRC breach went undetected for 70 days
- **Practical tools:** The frameworks exist but the implementation tooling doesn't
- **Affordable solutions:** Enterprise tools (OneTrust, BigID) are priced for corporations, not NGOs
- **Humanitarian context:** Generic GDPR tools don't understand the consent paradox, conflict-zone risks, or donor data-sharing tensions

**Amanat's positioning:** Not another framework or policy document. An agent that actually monitors, flags, and helps remediate data governance issues across the tools humanitarian organizations already use -- connected to their Google Workspace, SharePoint, Slack, and other platforms via Auth0 Token Vault.

---

## 10. Humanitarian OpenStreetMap Team (HOT) and Missing Maps -- Data Ethics Note

**Relevant concern:** When volunteers map previously unmapped areas (slums, refugee camps, informal settlements), the act of making these places visible can create harm. Documented case in India where local authorities used newly visible slum maps to conduct a crackdown.

Missing Maps addresses this by planning mapping projects "in collaboration with local people from the beginning" and ensuring all non-sensitive data is free, open, and available. But the ethical tension remains: mapping can simultaneously serve humanitarian purposes and enable surveillance.

Sources:
- [SciDev: Don't forget ethics when mapping uncharted slums](https://www.scidev.net/global/scidev-net-at-large/ethics-mapping-uncharted-slums/)
- [Evaluating ethical values of OpenStreetMap](https://www.tandfonline.com/doi/full/10.1080/10095020.2022.2087048)
