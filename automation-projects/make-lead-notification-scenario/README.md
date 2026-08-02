# Make (Integromat) — Lead Notification Scenario

Scenario that watches a lead source (CRM, form tool or webhook) for new entries and instantly notifies the sales team through Slack and email, with the lead also logged to a spreadsheet.

## Flow

1. **Watch Leads** (Webhook / CRM module) — triggers on every new lead.
2. **Router** — splits the flow into two parallel branches.
3. **Branch A — Slack** — sends a formatted message to a `#new-leads` channel with name, contact and source.
4. **Branch B — Google Sheets** — appends the lead as a new row for record-keeping.
5. **Email** — sends a confirmation/summary email to the sales owner.

## Setup notes

Make scenarios are stored as platform-specific blueprints (`.json`, tied to your Make organization's connections), so instead of a raw export this project documents the module-by-module configuration so it can be rebuilt in any Make account in a few minutes:

- **Module 1:** Webhook (custom) or native CRM trigger (e.g., HubSpot "Watch Leads").
- **Module 2:** Router with two routes (no filter needed, both run in parallel).
- **Module 3 (Route A):** Slack → "Create a Message".
- **Module 4 (Route B):** Google Sheets → "Add a Row".
- **Module 5:** Email → "Send an Email", triggered after Route B completes.

## Use case

Cuts lead response time by removing manual checking of forms/CRM inboxes, and keeps a running spreadsheet log for reporting without extra effort.
