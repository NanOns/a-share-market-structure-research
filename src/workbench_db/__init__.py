"""DuckDB data foundation for the unified workbench."""

from .owner import DatabaseOwner, DatabaseOwnerBusy
from .repository import WorkbenchRepository
from .read_repository import DuckDBReadRepository, PublicationReadRepository
from .postgres_write_repository import PostgresWriteRepository
from .config_store import ConfigVersionStore, DuckDBConfigVersionStore, PostgresConfigVersionStore, default_database_path
from .postgres_online_repository import PostgresOnlineRepository
from .postgres_research_repository import PostgresResearchRepository
from .result_object_repository import DuckDBResultObjectRepository, PostgresResultObjectRepository, ResultObjectRepository
from .slice_repository import DuckDBSliceRepository, PostgresSliceRepository, SliceRepository
from .operations_metadata import DuckDBOperationsMetadataReader, OperationsMetadataReader
from .publication_repository import (
    DuckDBPublicationRepositoryFactory,
    DuckDBPublicationStatusReader,
    PublicationRepositoryFactory,
    PublicationStatusReader,
)
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
    "default_database_path",
    "PostgresOnlineRepository",
    "PostgresResearchRepository",
    "ResultObjectRepository",
    "DuckDBResultObjectRepository",
    "PostgresResultObjectRepository",
    "SliceRepository",
    "DuckDBSliceRepository",
    "PostgresSliceRepository",
    "OperationsMetadataReader",
    "DuckDBOperationsMetadataReader",
    "PublicationRepositoryFactory",
    "DuckDBPublicationRepositoryFactory",
    "PublicationStatusReader",
    "DuckDBPublicationStatusReader",
    "ArtifactCatalogError",
    "PostgresArtifactCatalog",
    "AdapterHttpGateway",
    "BackendRepositoryProvider",
    "RepositoryUnavailable",
]
