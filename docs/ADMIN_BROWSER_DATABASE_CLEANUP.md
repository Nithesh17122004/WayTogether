# One-time database cleanup from the WayTogether admin dashboard

The Render Shell is not required. After this feature is deployed and enabled, sign in as a staff administrator and open:

`/admin/database-cleanup`

## How it works

1. The page requests a live dry-run from PostgreSQL. It displays counts without deleting records.
2. Review the preservation list and every deletion count.
3. Export a database backup before proceeding, or explicitly acknowledge the irreversible risk.
4. Type the exact confirmation phrase shown by the page and click the red cleanup button.
5. The server verifies the authenticated staff-admin identity, the short-lived signed preview token and that the current dry-run counts still match the preview.
6. The existing `cleanup_waytogether_data` command performs the operation inside a database transaction.
7. A Django admin audit-log marker records completion. The browser endpoint refuses a second execution.

## Preserved data

- All admin, staff and superuser accounts.
- Published journeys whose departure time has not passed.
- Driver accounts, profiles and vehicles needed by retained journeys.
- Approved verification documents for retained routes.

Other application users, non-upcoming journeys, bookings, expense settlements, payment attempts, notifications, messages, safety/review records, passenger-verification submissions and unrelated/outdated/unapproved driver documents are removed by the existing cleanup command.

## Enable and disable the browser action

The feature flag is disabled by default:

`ADMIN_DATABASE_CLEANUP_ENABLED=false`

Temporarily set it to `true` as a private environment variable on the `waytogether-api` Render service. After the cleanup is completed, set it back to `false`. The backend route is also protected by Django's `IsAdminUser` permission and a one-time completion marker.

The browser endpoint is not a substitute for a backup. The cleanup is destructive and must be reviewed before the final confirmation.
