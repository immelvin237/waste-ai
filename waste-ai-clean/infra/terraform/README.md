# Waste AI — Cloud Infrastructure (Terraform)

Provisions the optional cloud backend that the local sync worker uploads to:

- **S3** bucket (versioned, private) for anomaly / low-confidence images.
- **RDS PostgreSQL** (db.t3.micro, single-AZ) with a `transactions` table mirroring the local schema.
- **API Gateway (HTTP API) + Lambda (Python 3.11)** that validates and inserts sync payloads.
- **IAM** role with least-privilege logging permissions.

## Deploy

```bash
cd infra/terraform
terraform init
terraform plan  -var="db_password=ChangeMe_Strong123"
terraform apply -var="db_password=ChangeMe_Strong123"
terraform output api_url          # put this in ../../.env as AWS_API_URL
terraform output s3_bucket_name
```

## Notes

- The Lambda needs the `pg8000` package. Add it with a Lambda layer, or bundle it into the
  `lambda/` folder before `apply` (`pip install pg8000 -t lambda/`).
- RDS is set to `publicly_accessible = true` to keep this prototype simple; for production,
  place RDS and Lambda in a private VPC and restrict the security group.
- Destroy everything with `terraform destroy -var="db_password=..."`.
