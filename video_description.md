00:00 - 00:18: Introduction & Context

    00:00: The presentation begins with the title slide for amanat, describing it as a "Data Governance AI Agent" that runs locally to scan, evaluate, and remediate sensitive data.

    00:05: The "Problem" slide highlights issues with biometric data sharing without consent, Gender-Based Violence (GBV) reports sitting on publicly linked OneDrives, and medical details posted in public Slack channels.

    00:10: The "Amanat" slide details the technical stack, including an Auth0 Token Vault, Hybrid PII detection (using regex and Granite 4 Micro), Policy RAG (using BM25 retrieval from ICRC/GDPR PDFs), and local remediation capabilities.

    00:18: The presentation transitions to the "Demo" title slide.

00:19 - 00:41: Authentication & Setup

    00:19 - 00:23: The user initiates the Amanat web application on localhost:8000 and logs in using Auth0, verifying their identity via a push notification on their phone.

    00:26: The main Amanat dashboard appears, displaying options to connect cloud services.

    00:27 - 00:32: The user clicks "Connect Microsoft (OneDrive + Outlook)" and authorizes the required OAuth permissions (reading files, sending mail, etc.) on the Microsoft consent screen. A success message confirms the connection.

    00:34 - 00:37: The user proceeds to authorize Slack permissions for the "Waqwaq Relief Authority" workspace.

    00:40: Returning to the dashboard, the user creates a "New Chat" to begin issuing commands.

00:41 - 01:10: Scanning & Alerting via Outlook

    00:42: The screen splits, showing the Amanat interface on the left and an Outlook inbox on the right.

    00:44: The user prompts Amanat: "Search Outlook for emails containing beneficiary names or medical information. If you find violations, send a data protection alert email to both the sender and the recipient."

    00:45 - 00:58: Amanat searches Outlook, identifies PII (specifically name, phone_number, and medical_condition), and executes the send_email tool.

    01:00: Amanat provides a summary in the chat, confirming it found 5 messages with policy violations and sent alerts to the involved email addresses.

    01:06 - 01:09: In the Outlook window on the right, the newly generated "Data Protection Alert" email arrives in the inbox, containing a red warning box detailing the exact violation (referencing Case management system instead of chat).

01:10 - 01:31: Scanning & Alerting via Slack

    01:10: The right side of the split screen switches to Slack, displaying the #field-updates channel, which contains visible messages with survivor ages, medical statuses, and GPS coordinates.

    01:12: The user prompts Amanat: "Search Slack for messages containing beneficiary names, case numbers, or medical information in public channels."

    01:15 - 01:21: Amanat runs the search, utilizes the notify_channel tool, and immediately posts a "Data Protection Alert" directly into the #field-updates channel as an automated bot, flagging the presence of UNHCR case numbers and medical conditions.

    01:24: Amanat completes its report in the chat interface, listing the specific Slack channels it alerted.

    01:27 - 01:30: The user clicks through different Slack channels (#social, #data-governance) to verify the automated alerts were successfully distributed.

01:31 - 02:19: OneDrive Remediation (Revoking Access)

    01:31: The right side of the screen switches to a OneDrive file directory.

    01:35 - 01:42: The user navigates to WRA Operations > Protection. They open a PDF and a CSV file, both of which are marked as "Shared" and contain highly sensitive GBV incident data and personal identifiers.

    01:45: The user prompts Amanat: "Scan the Protection folder on OneDrive for files with PII that are publicly shared. Revoke sharing on those files and post an alert to #data-governance."

    01:52 - 01:56: Amanat scans the drive and pauses to ask for manual confirmation: "Confirm: revoke sharing" for the specific file IDs. The user clicks "Approve".

    02:00 - 02:07: Amanat successfully revokes the public sharing links, notifies the Slack channel, and outputs a summary of the remediated files (GBV_Incident_Report_Scanned.pdf and GBV_Incident_Reports_2026.csv).

    02:09 - 02:11: On the right side of the screen, the OneDrive interface updates in real-time, changing the "Sharing" status of those files from "Shared" to "Private".

    02:12 - 02:14: The user switches to the Slack window to verify the bot successfully posted the remediation alert in #data-governance.

02:19 - 02:55: OneDrive Remediation (Data Redaction)

    02:19: The user navigates to a new OneDrive folder: WRA Operations > Beneficiary Records.

    02:21 - 02:22: They open Catalysms_Displaced_Registry_2026.csv, showing a spreadsheet full of raw names, DOBs, phone numbers, GPS coordinates, and medical info.

    02:26: The user prompts Amanat: "Redact all PII from the Catalysms Displaced Registry on OneDrive and upload the redacted copy."

    02:30 - 02:38: Amanat processes the file and generates a report stating it found and redacted 47 instances of PII across 6 categories (special category data, location data, medical, etc.).

    02:35: Simultaneously, a new file titled REDACTED_Catalysms_Displaced_Registry_2026.csv appears in the OneDrive folder.

    02:40 - 02:52: The user opens the new REDACTED file. The screen shows that all sensitive data in the columns has been successfully replaced with bracketed placeholder tags (e.g., [MEDICAL REDACTED], [GPS REDACTED], [ETHNIC/RELIGIOUS REDACTED]).

02:56 - 02:57: Conclusion

    02:56: The video ends with a "Thank You!" slide displaying the developer's website, LinkedIn, and GitHub links.
