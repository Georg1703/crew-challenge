# AWS setup (done by hand by the owner)

Every JSON document pasted into the AWS console lives here. Placeholders: `<DEV_BUCKET>` (the
dev bucket's name), `<ACCOUNT_ID>` (12 digits, top right of the console). Never commit real ids
or keys. Region: `eu-central-1` (Frankfurt) for everything.

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

CloudFront with signed cookies on `media.<APP_DOMAIN>`, `cc-prod-media`, `cc-prod-backups`,
`cc-mediaconvert-prod`, IAM user `cc-prod-app`. Documents are added to `prod/` when we set it up;
the shared files above apply there too.
