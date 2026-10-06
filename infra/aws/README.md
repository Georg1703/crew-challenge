# AWS setup (done by hand by the owner)

Every JSON document pasted into the AWS console lives here. Placeholders: `<DEV_BUCKET>` and
`<PROD_BUCKET>` (the buckets' names), `<ACCOUNT_ID>` (12 digits, top right of the console),
`<APP_DOMAIN>` (the app's host, e.g. `crew.example.com`), `<DISTRIBUTION_ID>` (CloudFront).
Never commit real ids or keys. Region: `eu-central-1` (Frankfurt) for everything, except the
CloudFront certificate (`us-east-1`, which CloudFront requires).

```
infra/aws/
|-- media-lifecycle.json          # both media buckets
|-- mediaconvert-role-trust.json  # both MediaConvert roles
|-- dev/                          # local development
`-- prod/                         # production
```

## Dev (local development)

| Step | Where | What | File |
|---|---|---|---|
| 1 | S3 -> Create bucket | Private bucket for dev uploads | - |
| 2 | Bucket -> Permissions -> CORS | Browser PUT/GET from localhost and the phone tunnel, expose `ETag` | `dev/media-cors.json` |
| 3 | Bucket -> Management -> Lifecycle rule | Abort incomplete multipart uploads after 7 days | `media-lifecycle.json` |
| 4 | IAM -> Roles -> Create role `cc-mediaconvert-dev` | MediaConvert reads originals and writes renditions | `mediaconvert-role-trust.json`, `dev/mediaconvert-role-policy.json` |
| 5 | IAM -> Users -> Create user `cc-dev` | Your local credentials, dev bucket + MediaConvert only | `dev/user-policy.json` |
| 6 | Your Mac | `aws configure --profile cc-dev`, then `.env`: `AWS_PROFILE`, `MEDIA_BUCKET`, `MEDIACONVERT_ROLE_ARN` | - |
| 7 | Your Mac | Check: list the bucket, upload and delete a test file | - |

## Production (before release)

Media is private: the browser uploads with presigned URLs and reads through CloudFront on
`media.<APP_DOMAIN>`, opened per crew by signed cookies the API sets (`POST /api/v1/media/session`).
MediaConvert needs no console setup beyond its role: the job settings live in the code
(`backend/integrations/transcoding/mediaconvert.py`).

| Step | Where | What | File |
|---|---|---|---|
| 1 | S3 -> Create bucket | Private bucket for production media (Block all public access: on; default encryption SSE-S3: SSE-KMS would also need `kms:` permissions for uploads) | - |
| 2 | Bucket -> Permissions -> CORS | Browser PUT from the app, expose `ETag` | `prod/media-cors.json` |
| 3 | Bucket -> Management -> Lifecycle rule | Abort incomplete multipart uploads after 7 days | `media-lifecycle.json` |
| 4 | Your Mac | Make the cookie-signing key pair: `openssl genrsa -out cloudfront-private.pem 2048`, then `openssl rsa -pubout -in cloudfront-private.pem -out cloudfront-public.pem`. Never commit either file | - |
| 5 | CloudFront -> Key management -> Public keys -> Create | Paste `cloudfront-public.pem`; its ID is `CLOUDFRONT_KEY_PAIR_ID` | - |
| 6 | CloudFront -> Key management -> Key groups -> Create `cc-media` | With that public key | - |
| 7 | Certificate Manager in `us-east-1` -> Request | `media.<APP_DOMAIN>`, DNS validation | - |
| 8 | CloudFront -> Policies -> Response headers -> Create `cc-media-cors` | CORS: allow origin `https://<APP_DOMAIN>`, allow credentials, methods GET + HEAD, headers `Range`, origin override on (hls.js reads playlists and segments with cookies) | - |
| 9 | CloudFront -> Create distribution | Origin: the bucket, with a new origin access control (sign requests). Viewer: redirect HTTP to HTTPS, methods GET + HEAD, restrict viewer access with key group `cc-media`. Cache policy `CachingOptimized`, response headers policy `cc-media-cors`. Alternate domain `media.<APP_DOMAIN>` with the step 7 certificate. Price class: North America and Europe | - |
| 10 | Bucket -> Permissions -> Bucket policy | CloudFront reads `crews/*`; TLS only | `prod/media-bucket-policy.json` |
| 11 | Your DNS | `media.<APP_DOMAIN>` CNAME to the distribution's `*.cloudfront.net` name | - |
| 12 | IAM -> Roles -> Create role `cc-mediaconvert-prod` | MediaConvert reads originals and writes renditions | `mediaconvert-role-trust.json`, `prod/mediaconvert-role-policy.json` |
| 13 | IAM -> Users -> Create user `cc-prod-app` + access key | The server's credentials: media bucket + MediaConvert only (the backups statement comes with `backup-db.sh`) | `prod/app-user-policy.json` |
| 14 | Server `/opt/cc/.env` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `MEDIA_BUCKET`, `MEDIA_CDN_DOMAIN=media.<APP_DOMAIN>`, `CLOUDFRONT_KEY_PAIR_ID`, `CLOUDFRONT_PRIVATE_KEY_PATH`, `TRANSCODER_BACKEND=mediaconvert`, `MEDIACONVERT_ROLE_ARN`. Copy `cloudfront-private.pem` to the server root-only (`chmod 600`); the production compose file mounts it read-only into the backend and Celery containers | - |
