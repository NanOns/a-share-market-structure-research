"""DuckDB data foundation for the unified workbench."""

from .owner import DatabaseOwner, DatabaseOwnerBusy
from .repository import WorkbenchRepository
from .read_repository import DuckDBReadRepository, PublicationReadRepository
from .postgres_write_repository import PostgresWriteRepository
from .config_store import ConfigVersionStore, DuckDBConfigVersionStore, PostgresConfigVersionStore
from .postgres_online_repository import PostgresOnlineRepository
from .postgres_research_repository import PostgresResearchRepository
from .result_object_repository import DuckDBResultObjectRepository, PostgresResultObjectRepository, ResultObjectRepository
from .postgres_artifact_catalog import ArtifactCatalogError, PostgresArtifactCatalog
from .backend_provider import AdapterHttpGateway, BackendRepositoryProvider, RepositoryUnavailable
from .migrations import MigrationError, MigrationExecutor

__all__ = [
    "DatabaseOwner",
    "DatabaseOwnerBusy",
    "MigrationError",
    "MigrationExecutor",
    "WorkbenchRepository",
    "DuckDBReadRepository",
    "PublicationReadRepository",
    "PostgresWriteRepository",
    "ConfigVersionStore",
    "DuckDBConfigVersionStore",
    "PostgresConfigVersionStore",
    "PostgresOnlineRepository",
    "PostgresResearchRepository",
    "ResultObjectRepository",
    "DuckDBResultObjectRepository",
    "PostgresResultObjectRepository",
    "ArtifactCatalogError",
    "PostgresArtifactCatalog",
    "AdapterHttpGateway",
    "BackendRepositoryProvider",
    "RepositoryUnavailable",
]
