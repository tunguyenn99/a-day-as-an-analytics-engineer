"""CI guard: generated OpenMetadata workflows must parse with the pinned SDK.

Run with an environment that has openmetadata-ingestion installed. Uses dummy
connection values; nothing is contacted.
"""

import os

from metadata.generated.schema.metadataIngestion.workflow import (
    OpenMetadataWorkflowConfig,
)

from scripts import metadata_ingest

DUMMY = {
    "OPENMETADATA_HOST": "http://openmetadata:8585/api",
    "OPENMETADATA_JWT": "ci",
    "OPENMETADATA_SERVICE": "supabase",
    "PGHOST": "db",
    "PGUSER": "ci",
    "PGPASSWORD": "ci",
    "PGDATABASE": "postgres",
    "PGSSLMODE": "require",
}

if __name__ == "__main__":
    for key, value in DUMMY.items():
        os.environ.setdefault(key, value)
    for name, workflow in [
        ("database metadata", metadata_ingest.database_config()),
        ("dbt", metadata_ingest.dbt_config("full", "unused")),
    ]:
        OpenMetadataWorkflowConfig.model_validate(workflow)
        print(f"{name} workflow: valid")
