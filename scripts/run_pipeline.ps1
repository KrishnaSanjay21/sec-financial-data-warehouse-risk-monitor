$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    throw "Create .env from .env.example and set an identifying SEC_USER_AGENT first."
}

docker compose up -d postgres
docker compose --profile pipeline run --rm pipeline run-all

