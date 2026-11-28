# WayTogether database cleanup

The management command preserves:
- Platform administrator accounts (role=admin, staff accounts and superusers).
- Published journeys that have not departed yet.
- The driver account, driver profile and vehicle records needed by each retained journey.

It removes other accounts, non-upcoming journeys, bookings, finance/payment records, notifications, messages, emergency contacts, safety reports, reviews and identity/vehicle verification submissions. Stored uploaded files for deleted verification submissions and deleted driver profiles are deleted after the database transaction commits.

## Run safely on Render

1. Take a PostgreSQL backup from the Render database dashboard.
2. Open the backend service's Shell after the new deployment is live.
3. Run the dry run first:

   python manage.py cleanup_waytogether_data

4. Review every count. The dry run does not modify the database.
5. Only after the counts are correct, run:

   python manage.py cleanup_waytogether_data --execute

The cleanup is destructive. Keep the backup until the website, admin login and retained journey pages have been verified.

The command is intentionally not called by the deploy/start command. A deployment must never trigger a database wipe automatically.
