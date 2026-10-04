# GitHub Actions templates

These files are complete workflow templates but use the `.example` suffix, so GitHub does not activate them automatically.

To enable them:

1. Ensure the GitHub credential performing the change has the `workflow` scope.
2. Create `.github/workflows/`.
3. Copy `ci.yml.example` to `.github/workflows/ci.yml`.
4. Copy `refresh.yml.example` to `.github/workflows/refresh.yml`.
5. Add repository secrets `DATABASE_URL` and `SEC_USER_AGENT`.
6. Run the refresh workflow manually with a three-company limit and review `ingestion_run` and `dq_result` before enabling the 100-company schedule.

The refresh schedule is 11:17 UTC on weekdays. GitHub-hosted runners require a PostgreSQL endpoint that accepts secure connections from the runner; a database bound only to `localhost` will not be reachable.

