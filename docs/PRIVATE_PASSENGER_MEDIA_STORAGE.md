# Private passenger and driver identity document storage

Passenger Aadhaar proofs, passenger face photos, driving licences, driver face photos, RCs, insurance documents and vehicle photographs must not be written to the Render web service's ephemeral filesystem or exposed through a public bucket. This integration uses a dedicated Django storage alias for passenger verification only. The authenticated API streams a document to its owner or a staff reviewer; the frontend never receives a public object URL.

## Create a private Cloudflare R2 bucket

1. In Cloudflare Dashboard, open **Storage & databases → R2 → Overview** and create a Standard bucket, for example `waytogether-private-documents`.
2. Keep public access disabled. Do not enable the R2.dev public URL or attach a public custom domain.
3. Under **Manage API Tokens**, create a token with **Object Read & Write** permission, scoped to this bucket only.
4. Copy the Access Key ID and Secret Access Key immediately. Cloudflare does not show the secret again.
5. Copy the S3 endpoint shown by Cloudflare. It has the form `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.

Cloudflare's current R2 free tier includes 10 GB-month of Standard storage, 1 million Class A operations, and 10 million Class B operations each month; data egress is free. Usage beyond included amounts is billed at the published rates, so check current pricing before production use.

## Configure the Render API service

Open the **waytogether-api** web service in Render and add these environment variables. Add the secret values directly in Render; never commit them to Git or paste them into chat.

| Variable | Value |
| --- | --- |
| `PRIVATE_MEDIA_BUCKET_NAME` | Exact R2 bucket name |
| `PRIVATE_MEDIA_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `PRIVATE_MEDIA_ACCESS_KEY_ID` | R2 Access Key ID |
| `PRIVATE_MEDIA_SECRET_ACCESS_KEY` | R2 Secret Access Key |
| `PRIVATE_MEDIA_REGION_NAME` | `auto` |
| `PRIVATE_MEDIA_STORAGE_READY` | `true` — set this last, after verifying all preceding values |

Save the environment changes and wait for the API service to finish redeploying. The backend will not report uploads as enabled unless the explicit flag is true and the bucket name, HTTPS endpoint, access key, and secret are all present. Setting the flag alone cannot activate uploads.

## Driver and passenger uploads

The API uses the same private bucket configuration for a separate driver storage alias. Driver verification uploads (licence, driver face photo, RC, insurance and vehicle photo) remain disabled until all private storage variables are configured and `PRIVATE_MEDIA_STORAGE_READY=true`. The driver face photo must be JPG or PNG and is shown publicly only after manual approval and only while the driver has a published upcoming journey.

## Security and verification

- Keep the bucket private; do not make it public to make downloads work.
- Use a token scoped to this single bucket with Object Read & Write permissions.
- The API downloads documents only after checking the signed-in user is the document owner or a staff reviewer. Responses are marked `private, no-store`.
- Only masked Aadhaar copies should be accepted. The first eight digits must be hidden. Never upload a full unmasked Aadhaar number or biometric data.
- The application does not expose storage credentials or direct object URLs to the browser.
- On the Passenger → Identity verification page, the storage warning disappears only when the API confirms `uploads_enabled: true`. Until then, the submit button remains disabled and the API independently rejects uploads with HTTP 503.

## Cloudflare references

- [R2 S3-compatible API setup](https://developers.cloudflare.com/r2/get-started/s3/)
- [R2 API token permissions](https://developers.cloudflare.com/r2/api/tokens/)
- [R2 pricing and free tier](https://developers.cloudflare.com/r2/pricing/)
