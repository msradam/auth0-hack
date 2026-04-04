"""
Policy knowledge base for Amanat.
GDPR articles, ICRC data protection rules, and humanitarian data standards
formatted for Granite's <documents> RAG grounding.
"""

from pathlib import Path

POLICIES = [
    {
        "doc_id": 1,
        "title": "GDPR Article 5 - Principles relating to processing of personal data",
        "text": (
            "Personal data shall be: (a) processed lawfully, fairly and in a transparent manner; "
            "(b) collected for specified, explicit and legitimate purposes and not further processed "
            "in a manner that is incompatible with those purposes; (c) adequate, relevant and limited "
            "to what is necessary in relation to the purposes for which they are processed (data minimisation); "
            "(d) accurate and, where necessary, kept up to date; (e) kept in a form which permits identification "
            "of data subjects for no longer than is necessary (storage limitation); "
            "(f) processed in a manner that ensures appropriate security including protection against "
            "unauthorised or unlawful processing and against accidental loss, destruction or damage."
        ),
        "source": "GDPR",
    },
    {
        "doc_id": 2,
        "title": "GDPR Article 9 - Processing of special categories of personal data",
        "text": (
            "Processing of personal data revealing racial or ethnic origin, political opinions, religious "
            "or philosophical beliefs, trade union membership, genetic data, biometric data for the purpose "
            "of uniquely identifying a natural person, data concerning health, or data concerning a natural "
            "person's sex life or sexual orientation shall be prohibited. Exceptions include explicit consent, "
            "reasons of substantial public interest, or protecting vital interests of the data subject."
        ),
        "source": "GDPR",
    },
    {
        "doc_id": 3,
        "title": "GDPR Article 32 - Security of processing",
        "text": (
            "The controller and the processor shall implement appropriate technical and organisational measures "
            "to ensure a level of security appropriate to the risk, including: (a) pseudonymisation and encryption "
            "of personal data; (b) the ability to ensure the ongoing confidentiality, integrity, availability and "
            "resilience of processing systems; (c) the ability to restore the availability and access to personal "
            "data in a timely manner in the event of an incident; (d) a process for regularly testing, assessing "
            "and evaluating the effectiveness of technical and organisational measures."
        ),
        "source": "GDPR",
    },
    {
        "doc_id": 4,
        "title": "GDPR Article 44 - General principle for transfers to third countries",
        "text": (
            "Any transfer of personal data which are undergoing processing or are intended for processing after "
            "transfer to a third country or to an international organisation shall take place only if the controller "
            "and processor comply with the conditions laid down in this Chapter. All provisions of this Regulation "
            "shall be applied in order to ensure that the level of protection of natural persons guaranteed by this "
            "Regulation is not undermined."
        ),
        "source": "GDPR",
    },
    {
        "doc_id": 5,
        "title": "ICRC Rule 1 - Lawfulness and fairness of data processing",
        "text": (
            "Personal data must be processed fairly and lawfully. Processing is lawful when it is necessary for "
            "purposes mandated by the ICRC under the Geneva Conventions and its Statutes, or when the data subject "
            "has given consent. In humanitarian emergencies, processing may be lawful when necessary to protect the "
            "vital interests of the data subject or another person."
        ),
        "source": "ICRC Rules on Personal Data Protection",
    },
    {
        "doc_id": 6,
        "title": "ICRC Rule 3 - Data minimisation in humanitarian action",
        "text": (
            "Personal data must be adequate, relevant and not excessive in relation to the purposes for which they "
            "are processed. Humanitarian organisations must regularly review whether the data they hold is still "
            "necessary. Data that is no longer needed must be deleted or anonymised. The collection of biometric "
            "data requires particular justification given its sensitivity and the impossibility of changing such data."
        ),
        "source": "ICRC Rules on Personal Data Protection",
    },
    {
        "doc_id": 7,
        "title": "ICRC Rule 6 - Data security in humanitarian contexts",
        "text": (
            "Appropriate technical and organisational measures must be taken against unauthorised or unlawful "
            "processing and against accidental loss, destruction or damage of personal data. In conflict-affected "
            "areas, special attention must be given to the risk that data may be accessed by parties to the conflict. "
            "Data must be encrypted in transit and at rest. Access must be restricted to authorised personnel only. "
            "Physical security of devices carrying personal data must be ensured, especially during field missions."
        ),
        "source": "ICRC Rules on Personal Data Protection",
    },
    {
        "doc_id": 8,
        "title": "ICRC Rule 8 - International transfers of personal data",
        "text": (
            "Personal data shall only be transferred to a third party, including another humanitarian organisation, "
            "if the recipient ensures an adequate level of data protection. Before any transfer, a risk assessment "
            "must be conducted considering the nature of the data, the purpose of the transfer, and the legal and "
            "security environment of the recipient. Transfers of data about persons in detention or other vulnerable "
            "situations require heightened scrutiny."
        ),
        "source": "ICRC Rules on Personal Data Protection",
    },
    {
        "doc_id": 9,
        "title": "IASC Operational Guidance - Principle 2: Data minimisation",
        "text": (
            "Humanitarian organisations should only collect and process data that is necessary for the specific "
            "operational purpose. The impulse to collect as much data as possible 'just in case' must be resisted. "
            "Over-collection creates risk without proportionate benefit. Beneficiary data must not be shared with "
            "donors beyond what is strictly necessary for accountability, and individual-level data should be "
            "aggregated wherever possible."
        ),
        "source": "IASC Operational Guidance on Data Responsibility",
    },
    {
        "doc_id": 10,
        "title": "IASC Operational Guidance - Principle 5: Data security incident management",
        "text": (
            "Humanitarian organisations must have procedures to detect, report, and respond to data security "
            "incidents. Incidents involving personal data of affected populations must be treated with urgency "
            "given the potential for physical harm. In conflict zones, a data breach can lead to targeting, "
            "forced return, arbitrary detention, or loss of life. Organisations must maintain breach notification "
            "procedures and conduct regular security assessments."
        ),
        "source": "IASC Operational Guidance on Data Responsibility",
    },
    {
        "doc_id": 11,
        "title": "Do No Digital Harm - Humanitarian metadata risks",
        "text": (
            "Digital systems used in humanitarian action generate metadata that can reveal sensitive information "
            "about beneficiaries: location patterns, communication networks, religious practices, and political "
            "affiliations. Even when personal data is removed, metadata can enable re-identification. "
            "Humanitarian organisations must consider not only the data they collect intentionally but also the "
            "digital traces created by their systems and shared with technology providers."
        ),
        "source": "Privacy International / ICRC - The Humanitarian Metadata Problem",
    },
    {
        "doc_id": 12,
        "title": "Informed consent in humanitarian contexts",
        "text": (
            "Consent in humanitarian settings is inherently compromised because beneficiaries depend on aid for "
            "survival. When a person must provide data to receive food, shelter, or medical care, consent is not "
            "freely given. Humanitarian organisations must therefore rely on additional legal bases for processing "
            "and must implement robust safeguards regardless of whether consent was obtained. Consent forms must "
            "be in languages beneficiaries understand and must clearly explain how data will be used and shared."
        ),
        "source": "ICRC Handbook on Data Protection in Humanitarian Action",
    },
    {
        "doc_id": 13,
        "title": "GDPR Article 6(1)(e) - Processing in the public interest",
        "text": (
            "Processing is necessary for the performance of a task carried out in the public interest "
            "or in the exercise of official authority vested in the controller."
        ),
        "source": "GDPR",
        "tags": ["gdpr", "legal-basis", "public-interest", "humanitarian-exemption"],
    },
    {
        "doc_id": 14,
        "title": "GDPR Article 9(2)(c) and 9(2)(h) - Humanitarian exemptions for special category data",
        "text": (
            "Article 9(2)(c): Processing is necessary to protect the vital interests of the data subject "
            "or of another natural person where the data subject is physically or legally incapable of "
            "giving consent. "
            "Article 9(2)(h): Processing is necessary for the purposes of preventive or occupational medicine, "
            "for the assessment of the working capacity of the employee, medical diagnosis, the provision of "
            "health or social care or treatment or the management of health or social care systems and services "
            "on the basis of Union or Member State law or pursuant to contract with a health professional and "
            "subject to the conditions and safeguards referred to in paragraph 3."
        ),
        "source": "GDPR",
        "tags": ["gdpr", "special-categories", "vital-interests", "health", "humanitarian-exemption"],
    },
    {
        "doc_id": 15,
        "title": "ICRC Handbook Chapter 3 - Consent validity in humanitarian contexts",
        "text": (
            "In the emergency situations in which Humanitarian Organizations usually operate it can be "
            "difficult to fulfil the basic conditions of valid Consent, in particular that it is informed "
            "and freely given. For example, this can be the case where consenting to the Processing of "
            "Personal Data is a pre-condition to receive assistance. "
            "Consent should not be regarded as freely given if the Data Subject has no genuine and free "
            "choice or is unable to refuse or withdraw Consent without detriment or has not been informed "
            "sufficiently in order to understand the consequences of the Personal Data Processing. "
            "The Data Subject's vulnerability should be taken into account when considering the validity "
            "of Consent. Assessing vulnerability involves understanding the social, cultural and religious "
            "norms of the group to which Data Subjects belong and ensuring that each Data Subject is "
            "treated individually as the owner of his/her Personal Data."
        ),
        "source": "ICRC Handbook on Data Protection in Humanitarian Action (2nd ed., 2020), Chapter 3, Sections 3.2.3-3.2.4",
        "tags": ["icrc", "consent", "vulnerability", "humanitarian", "legal-basis"],
    },
    {
        "doc_id": 16,
        "title": "ICRC Handbook Section 2.8 - Data security in humanitarian operations",
        "text": (
            "Data security is a crucial component of an effective data protection system. Personal Data "
            "should be processed in a manner that ensures appropriate security of the Personal Data, "
            "including the prevention of unauthorized access to or use of Personal Data and the equipment "
            "used for the Processing. This is even more the case for the volatile environments in which "
            "Humanitarian Organizations often operate. In order to maintain security, the Data Controller "
            "should assess the specific risks inherent in the Processing and implement measures to mitigate "
            "those risks. These measures should ensure an appropriate level of security (taking into account "
            "available technology, prevailing security and logistical conditions and the costs of implementation) "
            "in relation to the nature of the Personal Data to be protected and the related risks."
        ),
        "source": "ICRC Handbook on Data Protection in Humanitarian Action (2nd ed., 2020), Chapter 2, Section 2.8.1",
        "tags": ["icrc", "data-security", "encryption", "access-control", "humanitarian"],
    },
    {
        "doc_id": 17,
        "title": "ICRC Handbook Section 2.7 - Data retention in humanitarian action",
        "text": (
            "Data should be retained for a defined period (e.g. three months, a year, etc.) for each "
            "category of data or documents. When it is not possible to determine at the time of collection "
            "how long data should be kept, an initial retention period should be set. Following the initial "
            "retention period, an assessment should be made as to whether the data should be deleted, or "
            "whether the data are still necessary to fulfil the purpose for which they were initially collected "
            "and further processed and, therefore, the initial retention period should be renewed for a "
            "limited period of time. When data have been deleted, all copies of the data should also be "
            "deleted. If the data have been shared with Third Parties, the Humanitarian Organization should "
            "take reasonable steps to ensure such Third Parties also delete the data."
        ),
        "source": "ICRC Handbook on Data Protection in Humanitarian Action (2nd ed., 2020), Chapter 2, Section 2.7",
        "tags": ["icrc", "retention", "deletion", "storage-limitation", "humanitarian"],
    },
    {
        "doc_id": 18,
        "title": "ICRC Rules on Personal Data Protection - Article 23: Limitations on Data Transfers",
        "text": (
            "Personal Data may be transferred only to the extent permitted by these rules. "
            "Data Transfers are subject to strict conditions: (a) Processing by the Recipient is restricted "
            "as much as possible to the specific purposes of ICRC Processing or permissible further Processing; "
            "(b) The amount and the type of Personal Data to be transferred is strictly limited to the "
            "Recipient's need to know for the specified purposes or for intended further Processing; "
            "(c) The transfer should not be incompatible with the reasonable expectations of the Data Subject. "
            "Depending on the sensitivity of the transfer and the risks it presents to individuals, additional "
            "protections may be necessary. A record of Data Transfers should be maintained. It may also be "
            "necessary to carry out a Data Protection Impact Assessment in connection with the data to be "
            "transferred."
        ),
        "source": "ICRC Rules on Personal Data Protection (2020), Article 23",
        "tags": ["icrc", "data-transfer", "data-sharing", "third-party", "impact-assessment"],
    },
    {
        "doc_id": 19,
        "title": "IASC Operational Guidance - All Principles for Data Responsibility in Humanitarian Action",
        "text": (
            "The Principles for Data Responsibility reflect the collective commitment of humanitarian actors. "
            "They are presented in alphabetical order: "
            "Accountability: Humanitarian organizations have an obligation to accept responsibility and be "
            "accountable for their data management activities to affected populations, internal governance "
            "structures, and national, regional and international actors. "
            "Confidentiality: Humanitarian organizations should implement appropriate organizational "
            "safeguards and procedures to keep sensitive data confidential at all times, including through "
            "clear and consistent access restrictions. "
            "Coordination and Collaboration: Coordinated and collaborative data management entails the "
            "meaningful inclusion of humanitarian partners, national and local authorities, and people "
            "affected by crisis in data management activities. "
            "Data Security: Humanitarian organizations should implement appropriate organizational and "
            "technical safeguards, procedures and systems to prevent, mitigate, report and respond to "
            "security breaches of both digital and non-digital data. "
            "Defined Purpose, Necessity and Proportionality: Humanitarian data management should have "
            "a clearly defined purpose and should be relevant, limited and proportionate to the specified "
            "purpose(s). "
            "Fairness and Legitimacy: Humanitarian organizations should manage data in a fair and legitimate "
            "manner enabling neutral and impartial delivery. "
            "Human Rights-Based Approach: Data management should respect, protect and promote the "
            "fulfillment of human rights, including equality and non-discrimination. "
            "People-Centered and Inclusive: Affected populations should be afforded an opportunity to "
            "participate in all steps of data management. "
            "Personal Data Protection: When managing personal data, humanitarian organizations have an "
            "obligation to adhere to applicable national and regional data protection laws or their own "
            "data protection policies. "
            "Quality: Data quality should be maintained such that owners, users and stakeholders can trust "
            "data management activities. "
            "Retention and Destruction: Organizations should establish a data retention and destruction "
            "schedule. Sensitive data should only be retained for as long as necessary to the specified "
            "purpose(s). "
            "Transparency: Organizations should manage data in ways that offer meaningful transparency "
            "toward humanitarian actors and stakeholders, particularly affected populations."
        ),
        "source": "IASC Operational Guidance on Data Responsibility in Humanitarian Action (2023), Section 2",
        "tags": ["iasc", "data-responsibility", "principles", "humanitarian", "accountability", "security"],
    },
    {
        "doc_id": 20,
        "title": "Sphere Handbook Protection Principle 1 - Sensitive information management",
        "text": (
            "Protection Principle 1: Enhance people's safety, dignity and rights and avoid exposing them "
            "to further harm. Humanitarian actors take steps to reduce overall risks and vulnerability of "
            "people, including to the potentially negative effects of humanitarian programmes. "
            "Sensitive information: Ensure that people are not put at risk as a result of the way that "
            "humanitarian actors record and share information. Establish a policy on collecting and "
            "referring sensitive information. It should define the circumstances under which information "
            "may be referred and respect the principle of informed consent. Failure to do so may "
            "compromise the safety of survivors and of staff. "
            "Managing sensitive information: Humanitarian organisations should have clear policies and "
            "procedures to guide staff on how to respond if they become aware of or witness abuses, and "
            "on how to make referrals to specialists or specialised agencies. The confidentiality of the "
            "information should be explained in those policies. Evidence such as witness statements, "
            "population profiles and images that allow people to be identified may be highly sensitive and "
            "can put people at risk."
        ),
        "source": "The Sphere Handbook: Humanitarian Charter and Minimum Standards (4th ed., 2018), Protection Principles",
        "tags": ["sphere", "protection", "sensitive-information", "do-no-harm", "confidentiality"],
    },
    # ─── GOVERNANCE RULES (docs 21-28) ────────────────────────────────
    # Operational evaluation criteria derived from ICRC, UNHCR, IASC, WFP,
    # GBVIMS, and Sphere frameworks. These tell the agent exactly what to
    # check when evaluating a scanned file.
    {
        "doc_id": 21,
        "title": "Humanitarian Data Classification - Sensitivity Tiers",
        "text": (
            "When evaluating a file, first classify its sensitivity using these tiers: "
            "TIER 4 - STRICTLY CONFIDENTIAL: GBV survivor data, child protection case files, "
            "witness statements, perpetrator information, protection assessments with individual "
            "identification. Maximum sharing: case worker + direct supervisor only. Never on shared "
            "drives. Never in donor reports. Encrypt at rest. DPIA required. "
            "TIER 3 - CONFIDENTIAL: Biometric data (fingerprints, iris scans, facial recognition), "
            "medical/health records, beneficiary registration with full PII (names + IDs + locations), "
            "staff security information, national ID numbers. Maximum sharing: authorized programme "
            "staff with role-based access. Encrypt at rest and in transit. "
            "TIER 2 - INTERNAL: Aggregated programme statistics, needs assessments, operational "
            "coordination data (3W), staff contact lists. May be shared org-wide for operational "
            "purposes. Not for public release without review. "
            "TIER 1 - PUBLIC: Published reports, situation updates, anonymized aggregates. "
            "No restrictions on dissemination."
        ),
        "source": "Synthesized from UN ST/SGB/2007/6, OCHA Data Responsibility Guidelines (2021), ICRC Rules",
        "tags": ["classification", "sensitivity", "tiers", "evaluation"],
    },
    {
        "doc_id": 22,
        "title": "Sharing Violations - What Triggers a Finding",
        "text": (
            "CRITICAL violations (must remediate immediately): "
            "1. Any TIER 4 data (GBV, protection, child protection) shared beyond case team = CRITICAL. "
            "Cite: Sphere Protection Principle 1, GBVIMS Information Sharing Protocol. "
            "2. Any TIER 3 data (biometric, medical, full beneficiary PII) with public link = CRITICAL. "
            "Cite: GDPR Article 9, ICRC Rule 6. "
            "3. UNHCR case numbers or refugee status information accessible to anyone with link = CRITICAL. "
            "Cite: UNHCR GDPP 2022, GDPR Article 5. "
            "4. GPS coordinates of beneficiary shelters/locations with any external sharing = CRITICAL. "
            "Cite: Do No Digital Harm, Privacy International/ICRC. "
            "WARNING violations (should remediate within 7 days): "
            "5. TIER 3 data shared org-wide instead of restricted to programme team = WARNING. "
            "Cite: IASC Confidentiality principle, ICRC Rule 6. "
            "6. Beneficiary names + contact information shared org-wide = WARNING. "
            "Cite: GDPR Article 5 data minimisation. "
            "7. Staff personal mobile numbers on shared drive = WARNING. "
            "Cite: ICRC Rule 6 (staff in sensitive locations face security risk). "
            "INFO (note for awareness): "
            "8. Aggregated data shared org-wide = INFO (acceptable if no small-group re-identification risk)."
        ),
        "source": "Synthesized from GBVIMS ISP, UNHCR GDPP, IASC Guidance, ICRC Handbook",
        "tags": ["sharing", "access-control", "violations", "evaluation"],
    },
    {
        "doc_id": 23,
        "title": "Retention Violations - When Data Has Been Kept Too Long",
        "text": (
            "Evaluate file age (last_modified date) against these retention thresholds: "
            "GBV/protection case files: retain only for duration of active case. After case closure, "
            "archive with restricted access. If file has not been modified in >6 months and contains "
            "GBV/protection data, flag for retention review. Cite: ICRC Handbook Section 2.7. "
            "Beneficiary registration data: retain for programme duration + donor audit period "
            "(typically 5-7 years after programme end). If file is >2 years old and contains full "
            "beneficiary PII, flag for retention review. Cite: ICRC Handbook Section 2.7, IASC Retention principle. "
            "Medical/health records: retain per statutory obligations of operational country (typically "
            "5-10 years). If file is >1 year old and shared beyond medical team, flag. "
            "Biometric enrollment data: review necessity every 6 months. Biometric data creates "
            "permanent identifiable records and cannot be changed if compromised. Cite: ICRC Rule 3. "
            "General rule: if a file containing PII has not been modified in >12 months, flag for "
            "retention review. Data no longer needed must be deleted or anonymized. All copies must "
            "also be deleted. If shared with third parties, take reasonable steps to ensure they delete too."
        ),
        "source": "Synthesized from ICRC Handbook S.2.7, IASC Guidance, UNHCR Policy, donor audit requirements",
        "tags": ["retention", "file-age", "deletion", "evaluation"],
    },
    {
        "doc_id": 24,
        "title": "Data Minimisation Violations - Over-Collection and Over-Storage",
        "text": (
            "A file violates data minimisation if: "
            "1. It contains 4 or more categories of PII in a single file (names + IDs + medical + "
            "location + biometric). This suggests data has not been separated by purpose. "
            "Cite: GDPR Article 5(c), ICRC Rule 3. "
            "2. It contains special category data (medical, ethnic, religious, biometric) alongside "
            "direct identifiers (names, ID numbers) when the purpose could be served with "
            "pseudonymized or aggregated data. Cite: UNHCR DPIA minimisation principle. "
            "3. Biometric data is collected when a simpler identifier would suffice. "
            "Cite: ICRC Biometrics Policy. "
            "4. Individual-level beneficiary data is included in donor reports when aggregate "
            "statistics would satisfy the reporting requirement. "
            "Cite: IASC Defined Purpose/Necessity/Proportionality principle. "
            "5. A file references 'unencrypted drive' or 'USB' for sensitive data storage. "
            "Cite: ICRC Handbook Section 2.8, WFP centralized storage policy."
        ),
        "source": "Synthesized from GDPR Art 5, ICRC Rules, UNHCR DPIA Framework, WFP Guide",
        "tags": ["minimisation", "over-collection", "purpose-limitation", "evaluation"],
    },
    {
        "doc_id": 25,
        "title": "External Transfer Violations - When Data Should Not Leave the Organization",
        "text": (
            "External data sharing requires all of: (a) written data-sharing agreement, "
            "(b) recipient meets comparable data protection standards, (c) DPIA completed, "
            "(d) data anonymized or pseudonymized where possible, (e) limited to recipient's "
            "need to know. "
            "CRITICAL violations: "
            "1. GBV survivor data shared externally in any identifiable form = CRITICAL. "
            "Only non-identifiable compiled data may be shared via formal ISP. "
            "Cite: GBVIMS ISP, Sphere Protection Principle 1. "
            "2. Beneficiary list with names and case numbers sent to external auditor/donor "
            "without anonymization = CRITICAL. Donors receive disaggregated indicators in "
            "aggregate format (percentages), not individual records. "
            "Cite: ICRC Rules Article 23, IASC Transparency principle. "
            "3. Public link sharing on any file with PII = de facto uncontrolled external transfer. "
            "Cite: ICRC Rules Article 23, GDPR Article 44. "
            "WARNING: "
            "4. File shared with 'external audit team' email without data sharing agreement = WARNING. "
            "Cite: IFRC Data Protection Policy."
        ),
        "source": "Synthesized from ICRC Rules Art 23, IFRC Policy, GBVIMS ISP, IASC Guidance",
        "tags": ["transfer", "external-sharing", "donor-reporting", "evaluation"],
    },
    {
        "doc_id": 26,
        "title": "GBV and Protection Data - Highest Sensitivity Rules",
        "text": (
            "GBV survivor data and protection case files require the strictest handling: "
            "IDENTIFICATION: A file is likely GBV/protection data if its name or content contains: "
            "GBV, incident report, protection assessment, violence, abuse, safeguarding, "
            "survivor, perpetrator, case management, SGBV, or child protection. "
            "RULES: "
            "1. SHARING: Maximum scope is case worker + direct supervisor. Need-to-know only. "
            "If shared with anyone else (org-wide, public link, specific people beyond case team), "
            "this is a CRITICAL violation. Cite: Sphere Protection Principle 1. "
            "2. STORAGE: Must be in a system with role-based access control (e.g. Primero/GBVIMS+). "
            "Must NOT be on general shared drives, personal OneDrive, or unencrypted storage. "
            "If found on OneDrive with any sharing, flag as CRITICAL. "
            "3. CONTENT: Even file NAMES should not reveal survivor identity. A filename like "
            "'GBV_Incident_Reports' is acceptable, but 'Fatima_GBV_Case' is a violation. "
            "4. INTER-AGENCY: Only non-identifiable, compiled data may be shared via a formal "
            "Information Sharing Protocol. Individual case data never crosses organizational boundaries. "
            "5. DONOR REPORTING: Never include identifiable GBV data in donor reports. "
            "Aggregate statistics only (e.g. '47 GBV cases referred to services in Q1')."
        ),
        "source": "Synthesized from GBVIMS ISP, Sphere Handbook, IASC GBV Guidelines, ICRC Handbook",
        "tags": ["gbv", "protection", "highest-sensitivity", "evaluation"],
    },
    {
        "doc_id": 27,
        "title": "Biometric Data - Special Handling Rules",
        "text": (
            "Biometric data (fingerprints, iris scans, facial recognition, retina scans) requires "
            "special handling because it creates a permanently identifiable record that cannot be "
            "changed if compromised: "
            "IDENTIFICATION: A file contains biometric data if it references fingerprint, iris scan, "
            "facial recognition, retina, biometric enrollment, or biometric registration. "
            "RULES: "
            "1. DPIA REQUIRED: A Data Protection Impact Assessment must be completed before any "
            "biometric data collection. If biometric data exists without documented DPIA, flag. "
            "Cite: ICRC Biometrics Policy. "
            "2. COLLECTION NECESSITY: Biometric data should only be collected when simpler "
            "identifiers (cards, PINs, case numbers) are insufficient. Flag if biometrics appear "
            "alongside simpler identifiers that could serve the same purpose. Cite: ICRC Rule 3. "
            "3. STORAGE: Must be encrypted. Hardware-supported encryption preferred (WFP/SCOPE model). "
            "No biometric data on personal devices, USB drives, or unencrypted field laptops. "
            "If file mentions 'unencrypted drive' or 'USB' for biometric storage, flag as CRITICAL. "
            "4. ACCESS: Restricted to system administrators and authorized processors only. "
            "If shared org-wide or via link, this is CRITICAL. Cite: ICRC Rules. "
            "5. REGISTER: All processing operations on biometric data must be recorded in a register. "
            "Cite: ICRC Rules on Personal Data Protection."
        ),
        "source": "Synthesized from ICRC Biometrics Policy, ICRC Rules, WFP Guide to Personal Data Protection",
        "tags": ["biometric", "fingerprint", "iris", "special-handling", "evaluation"],
    },
    {
        "doc_id": 28,
        "title": "Humanitarian Data Audit Checklist - What to Evaluate for Each File",
        "text": (
            "For every file scanned, evaluate these dimensions in order: "
            "1. CONTENT: What PII categories are present? (names, IDs, medical, ethnic/religious, "
            "biometric, GPS coordinates, case numbers). More categories = higher risk. "
            "2. SENSITIVITY TIER: Classify using doc_id 21. Tier 4 = strictest, Tier 1 = open. "
            "3. SHARING SCOPE: Is the current sharing appropriate for the sensitivity tier? "
            "Check against doc_id 22. Public link on Tier 3/4 data = always CRITICAL. "
            "4. FILE AGE: When was the file last modified? Check against retention thresholds "
            "in doc_id 23. Stale files with PII must be reviewed for deletion. "
            "5. DATA MINIMISATION: Does the file contain more data categories than necessary "
            "for its apparent purpose? Check against doc_id 24. "
            "6. EXTERNAL EXPOSURE: Could the data reach people outside the organization via "
            "current sharing settings? Check against doc_id 25. "
            "7. SPECIAL TYPES: If GBV/protection data, apply doc_id 26 rules. "
            "If biometric data, apply doc_id 27 rules. "
            "8. STORAGE SECURITY: Are there references to unencrypted storage, USB drives, "
            "or personal devices for sensitive data? "
            "Report each violation with: severity (CRITICAL/WARNING/INFO), the specific rule "
            "from docs 21-27 that was violated, and a concrete remediation action."
        ),
        "source": "Synthesized from UNHCR DPIA Framework 12 Privacy Principles, ICRC Handbook, IASC Guidance",
        "tags": ["audit", "checklist", "evaluation", "workflow"],
    },
]


# --- Real policy chunks extracted from source PDFs via Docling ---
# These are loaded from policy_chunks.json (generated by scripts/preprocess_policies.py)
# and used for RAG grounding with Granite 4's native <documents> format.

_REAL_CHUNKS: list[dict] | None = None
_BM25_INDEX = None
_BM25_CORPUS: list[list[str]] | None = None


def _load_real_chunks() -> list[dict]:
    """Load preprocessed policy chunks from source PDFs and build BM25 index."""
    global _REAL_CHUNKS, _BM25_INDEX, _BM25_CORPUS
    if _REAL_CHUNKS is not None:
        return _REAL_CHUNKS

    import json
    chunks_path = Path(__file__).parent / "policy_chunks.json"
    if chunks_path.exists():
        with open(chunks_path) as f:
            _REAL_CHUNKS = json.load(f)
    else:
        _REAL_CHUNKS = []
        return _REAL_CHUNKS

    # Build BM25 index over chunk text + titles
    from rank_bm25 import BM25Okapi
    _BM25_CORPUS = []
    for chunk in _REAL_CHUNKS:
        tokens = (chunk.get("title", "") + " " + chunk.get("text", "")).lower().split()
        _BM25_CORPUS.append(tokens)
    _BM25_INDEX = BM25Okapi(_BM25_CORPUS)

    return _REAL_CHUNKS


def search_real_policies(query: str, max_results: int = 8) -> list[dict]:
    """Search the real PDF-extracted policy chunks using BM25 ranking.

    BM25 (Best Match 25) handles term frequency, inverse document frequency,
    and document length normalization — much better than raw keyword matching
    for policy documents where the same concept is expressed in different terms.

    Returns chunks from the actual ICRC Handbook, IASC Guidance, GDPR,
    and Sphere Handbook — not hand-written paraphrases.
    """
    chunks = _load_real_chunks()
    if not chunks or _BM25_INDEX is None:
        return search_policies(query, max_results)

    query_tokens = query.lower().split()
    scores = _BM25_INDEX.get_scores(query_tokens)

    # Get top-scoring chunks
    scored = [(score, i) for i, score in enumerate(scores) if score > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [chunks[i] for _, i in scored[:max_results]]


def get_documents_for_prompt(policy_ids: list[int] | None = None) -> str:
    """Format policies as Granite <documents> block for system prompt injection.

    Uses the real PDF-extracted chunks when available, falling back to
    hand-written POLICIES. Granite 4's native RAG format:
    <documents>
    {"doc_id": 1, "title": "...", "text": "...", "source": "..."}
    </documents>
    """
    import json

    # If specific policy_ids requested, use the hand-written POLICIES
    # (these are referenced by the rules engine by doc_id)
    if policy_ids is not None:
        docs = [p for p in POLICIES if p["doc_id"] in policy_ids]
        if not docs:
            return ""
        lines = []
        for doc in docs:
            compact = {
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "source": doc["source"],
                "text": doc["text"][:300],
            }
            lines.append(json.dumps(compact))
        return "<documents>\n" + "\n".join(lines) + "\n</documents>"

    # Otherwise use all hand-written policies in compact form
    lines = []
    for doc in POLICIES:
        compact = {
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "source": doc["source"],
            "text": doc["text"][:300],
        }
        lines.append(json.dumps(compact))
    return "<documents>\n" + "\n".join(lines) + "\n</documents>"


def get_rag_documents(query: str, max_docs: int = 5) -> str:
    """Search real policy PDFs and format as Granite <documents> block.

    This is the primary RAG function for policy questions. It searches
    the actual ICRC Handbook, IASC Guidance, GDPR, and Sphere Handbook
    text extracted from PDFs via Docling, then formats the results in
    Granite 4's native document grounding format.

    For scan/remediation queries, the rules engine provides policy
    citations directly — this function is for open-ended policy questions.
    """
    import json
    chunks = search_real_policies(query, max_results=max_docs)
    if not chunks:
        return ""

    lines = []
    for chunk in chunks:
        doc = {
            "doc_id": chunk.get("doc_id", 0),
            "title": chunk.get("title", ""),
            "source": f"{chunk.get('source', '')} — {chunk.get('full_source', '')}",
            "text": chunk["text"][:800],  # Truncate for Granite Micro context
        }
        lines.append(json.dumps(doc))
    return "<documents>\n" + "\n".join(lines) + "\n</documents>"


def search_policies(query: str, max_results: int = 5) -> list[dict]:
    """Keyword search over hand-written policy documents.

    Used by the rules engine for violation citations. For RAG grounding
    of policy questions, use search_real_policies() instead.
    """
    query_terms = query.lower().split()
    scored = []
    for policy in POLICIES:
        tags_str = " ".join(policy.get("tags", []))
        text = (policy["title"] + " " + policy["text"] + " " + tags_str).lower()
        score = sum(1 for term in query_terms if term in text)
        if score > 0:
            scored.append((score, policy))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_results]]
