# Deployment Guide

This guide covers deploying the ingestion service to Google Cloud Run.

## Prerequisites

1. GCP Project with billing enabled
2. `gcloud` CLI installed and authenticated
3. Terraform installed
4. Docker installed (for building images)

## Setup Steps

### 1. Create Secret Manager Secrets

Create two separate secrets for the CDP API credentials:

```bash
# Extract the key name and private key from your JSON file
# Get values from your .env file or Coinbase CDP API key
KEY_NAME="organizations/.../apiKeys/{key_id}"
PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\n..."

# Create secret for API key name
echo -n "$KEY_NAME" | gcloud secrets create vibe-trade-coinbase-cdp-key-name \
  --data-file=- \
  --project=vibe-trade-475704 \
  --replication-policy="automatic"

# Create secret for private key
echo -n "$PRIVATE_KEY" | gcloud secrets create vibe-trade-coinbase-cdp-key-secret \
  --data-file=- \
  --project=vibe-trade-475704 \
  --replication-policy="automatic"
```

**Note**: If you don't have `jq`, you can manually extract the values from the JSON file and create the secrets separately.

### 2. Configure Terraform Variables

Update `vibe-trade-terraform/terraform.tfvars` with your values:

```hcl
coinbase_environment = "live"  # or "sandbox"
coinbase_symbols     = "BTC-USD,ETH-USD"  # comma-separated list
```

### 3. Apply Terraform

Deploy the infrastructure:

```bash
cd vibe-trade-terraform
terraform init
terraform plan
terraform apply
```

This will create:
- Artifact Registry repository for ingestion images
- Service account for the ingestion service
- Secret Manager secrets (if not already created)
- Cloud Run service (will be ready after image is pushed)

### 4. Build and Push Docker Image

Get the Artifact Registry URL from Terraform:

```bash
REGISTRY_URL=$(cd vibe-trade-terraform && terraform output -raw artifact_registry_url_ingestion)
echo $REGISTRY_URL
```

Build and push the image:

```bash
cd vibe-trade-ingestion

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build the image
docker build -t $REGISTRY_URL/vibe-trade-ingestion:latest .

# Push the image
docker push $REGISTRY_URL/vibe-trade-ingestion:latest
```

### 5. Verify Deployment

Check the Cloud Run service status:

```bash
gcloud run services describe vibe-trade-ingestion \
  --region=us-central1 \
  --format="value(status.url)"
```

View logs:

```bash
gcloud run services logs read vibe-trade-ingestion \
  --region=us-central1 \
  --limit=50
```

## Configuration

### Environment Variables

The service uses these environment variables:

**Cloud Run (set via Terraform):**
- `COINBASE_ENVIRONMENT`: `sandbox` or `live` (from `terraform.tfvars` → `var.coinbase_environment`, default: `live`)
- `COINBASE_SYMBOLS`: Comma-separated list of symbols (from `terraform.tfvars` → `var.coinbase_symbols`, default: `BTC-USD,ETH-USD`)
- `COINBASE_CDP_KEY_NAME`: API key name from Secret Manager
- `COINBASE_CDP_KEY_SECRET`: Private key from Secret Manager

**Local Development:**
- `COINBASE_ENVIRONMENT`: `sandbox` or `live` (default: `live`)
- `COINBASE_SYMBOLS`: Comma-separated list of symbols (default: `BTC-USD,ETH-USD`)
- `COINBASE_CDP_KEY_NAME`: API key name (from `.env` file or environment variable)
- `COINBASE_CDP_KEY_SECRET`: Private key (from `.env` file or environment variable)
- `COINBASE_USE_FULL_API_KEY_NAME`: `true` or `false` (default: `false`, uses key ID only)

### Secret Manager

The CDP API credentials are stored in two separate Secret Manager secrets:
- `vibe-trade-coinbase-cdp-key-name`: Contains the API key name
- `vibe-trade-coinbase-cdp-key-secret`: Contains the private key

These are injected as environment variables in Cloud Run.

## Updating the Service

To update the service after code changes:

1. Build and push a new image:
   ```bash
   docker build -t $REGISTRY_URL/vibe-trade-ingestion:latest .
   docker push $REGISTRY_URL/vibe-trade-ingestion:latest
   ```

2. Cloud Run will automatically use the latest image (if using `:latest` tag)

3. Or manually update the service:
   ```bash
   gcloud run services update vibe-trade-ingestion \
     --image $REGISTRY_URL/vibe-trade-ingestion:latest \
     --region=us-central1
   ```

## Troubleshooting

### Service Won't Start

1. Check logs:
   ```bash
   gcloud run services logs read vibe-trade-ingestion --region=us-central1
   ```

2. Verify Secret Manager secrets exist and are accessible:
   ```bash
   gcloud secrets versions access latest --secret="vibe-trade-coinbase-cdp-key-name"
   gcloud secrets versions access latest --secret="vibe-trade-coinbase-cdp-key-secret"
   ```

3. Verify service account has Secret Manager access:
   ```bash
   gcloud projects get-iam-policy vibe-trade-475704 \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:vibe-trade-ingestion-runner@vibe-trade-475704.iam.gserviceaccount.com"
   ```

### Secret Not Found

If the secrets are not found, verify:
- Secret Manager secrets exist: `gcloud secrets list | grep coinbase-cdp`
- Both secrets have versions: Check with `gcloud secrets versions list`
- Service account has `roles/secretmanager.secretAccessor` permission

### API Authentication Errors

If you see 401 errors:
- Verify the CDP key file format is correct (valid JSON with `name` and `privateKey` fields)
- Check that `COINBASE_ENVIRONMENT` matches your key's environment
- Verify the key hasn't been revoked in Coinbase

## Cost Considerations

- **Cloud Run**: Charges for CPU and memory usage while the service is running
- **Min Instances**: Set to 1 to keep service warm (avoids cold starts but incurs continuous cost)
- **Estimated Cost**: ~$10-15/month for 1 instance running 24/7 with 1 CPU and 512Mi memory

To reduce costs, you can:
- Set `min_instance_count = 0` (but will have cold starts)
- Reduce CPU/memory if usage is low
- Use Cloud Scheduler + Cloud Run Jobs instead (only runs when triggered)

