# Zapier — Form to Sheets Zap

Zap that syncs new form submissions (Typeform, Google Forms, etc.) into a spreadsheet and sends the submitter a confirmation email automatically.

## Flow

1. **Trigger — New Form Submission** (Typeform / Google Forms / Jotform).
2. **Action 1 — Google Sheets: Create Spreadsheet Row** — logs the submission with a timestamp.
3. **Action 2 — Formatter by Zapier** — normalizes fields (e.g., trims text, formats phone numbers).
4. **Action 3 — Gmail/Email: Send Email** — sends a confirmation message to the submitter using the data from step 1.

## Setup notes

Zaps live inside a Zapier account and aren't exported as a portable file, so this project documents the exact step configuration so it can be recreated directly in the Zapier editor:

- **Trigger app:** your form tool of choice, event = "New Entry/Response".
- **Action 1:** Google Sheets → connect the target spreadsheet, map form fields to columns.
- **Action 2 (optional):** Formatter → Text/Date utilities for cleanup before storage.
- **Action 3:** Gmail/Outlook → "To" = submitter's email field, dynamic subject/body using form data.

## Use case

Removes manual copy-paste from form responses into spreadsheets and guarantees every submitter gets an instant, consistent confirmation.
