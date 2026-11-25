# Phase 4 — Driver, vehicle and document verification

## Driver profile
- One profile per Driver account.
- Profile includes city, state and a short introduction.
- Status values: draft, pending, approved, needs_resubmission, suspended.
- Only active Driver accounts with verified email and phone can use the driver endpoints.

## Vehicle registration
- Drivers can register multiple vehicles.
- Store registration number, make, model, manufacture year, colour, type and passenger seat count.
- Registration number is normalised to uppercase without whitespace.
- Driver must attest the vehicle is privately used and is not being registered as a commercial taxi.
- Vehicle status is tracked separately from driver status.
- Approved vehicle identity fields cannot be edited through the current API.

## Documents
Supported types:
- Driving licence (driver-level, no vehicle link)
- Vehicle registration certificate (vehicle-level)
- Insurance certificate (vehicle-level)
- Pollution certificate (vehicle-level, optional in this workflow where applicable)
- Vehicle photograph (vehicle-level)

Validation:
- PDF, JPG/JPEG and PNG signatures are checked.
- Maximum file size is 8 MB per document.
- File extension and supplied content type must agree.
- Each upload gets a random private storage name.
- A new upload supersedes the previous current document for that type/vehicle, while prior metadata remains in the database.
- Expiry date can be stored and expired documents are not accepted as valid for submission.

## Submission requirements
Before a vehicle can be submitted:
- Current driving licence exists.
- Current vehicle registration document exists.
- Current insurance document exists.
- Current vehicle photograph exists.
- Required documents must not be expired.

The driver submits a specific vehicle. Documents can have been uploaded before submission. Admin review is performed per current document.

## Administrator workflow
1. Staff account opens the pending document queue.
2. Staff downloads the private file through the protected endpoint.
3. Staff approves or rejects the current document.
4. Rejection requires a note explaining the correction.
5. A vehicle becomes approved when all required vehicle documents are current and approved.
6. A driver becomes approved when the current driving licence is approved and at least one vehicle is approved.
7. If a current required document is rejected or expired, the relevant status moves to needs_resubmission.

All review decisions store reviewer and timestamp. Only staff can read the queue, make review decisions or download another user's document.

## API routes
Prefix: `/api/v1/drivers/`

- `GET/PATCH profile/`
- `GET/POST vehicles/`
- `GET vehicles/{id}/`
- `GET/POST documents/`
- `GET documents/{id}/download/`
- `POST verification/submit/`
- `GET admin/verification/queue/`
- `POST admin/verification/documents/{id}/review/`

## Production prerequisites
The current file field uses Django's default storage below a private local MEDIA_ROOT. Production must use persistent private storage and must not serve MEDIA_ROOT as a public directory. Configure malware scanning, backups, retention/deletion rules, monitoring and access controls. Review legal basis, privacy notices and document-retention periods before collecting real identity documents.

The PUC document is supported as an optional upload in this workflow; confirm state- and vehicle-specific requirements before launch.
