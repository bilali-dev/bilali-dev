# n8n — API to Spreadsheet

Scheduled workflow that fetches data from a REST API, normalizes the JSON payload, and appends each record as a row in a Google Sheet (adaptable to Excel Online).

## Flow

1. **Schedule Trigger** — runs every day at a fixed time (cron).
2. **HTTP Request** — calls the target API endpoint (supports query params / auth headers).
3. **Set** — maps the relevant fields from the JSON response into a flat row structure.
4. **Google Sheets (Append)** — inserts the mapped row into the destination spreadsheet.

## Import

Import [`workflows/workflow.json`](./workflows/workflow.json) directly into n8n via **Workflows → Import from File**, then:

- Set your API URL and credentials in the **HTTP Request** node.
- Connect your Google Sheets credential and select the target spreadsheet/sheet in the **Google Sheets** node.
- Adjust the cron expression in the **Schedule Trigger** node.

## Use case

Useful for daily reporting, price/inventory monitoring, or syncing any external API into a spreadsheet without writing a standalone script.
