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
from .operations_metadata import PostgresOperationsMetadataReader
from .publication_repository import (
    DuckDBPublicationRepositoryFactory,
    DuckDBPublicationStatusReader,
    PostgresPublicationStatusReader,
    PostgresPublicationBackend,
    PostgresPublicationBackendFactory,
    PublicationRepositoryFactory,
    PublicationStatusReader,
)
from .analysis_activation_repository import AnalysisActivationRepository, DuckDBAnalysisActivationRepository, PostgresAnalysisActivationRepository
from .history_job_repository import HistoryJobRepository, HistoryJobStore, DuckDBHistoryJobRepository, DuckDBHistoryJobStore
from .postgres_history_job_repository import PostgresHistoryJobRepository
from .postgres_publication_writer import PostgresPublicationWriter
from .incremental_writer_repository import IncrementalWriterRepository, DuckDBIncrementalWriterRepository
from .research_builder_repository import ResearchBuilderRepository, DuckDBResearchBuilderRepository
from .backup_repository import BackupRepository, DuckDBBackupRepository
from .backup_catalog_repository import BackupCatalogRepository, DuckDBBackupCatalogRepository, PostgresBackupCatalogRepository
from .storage_connection import StorageConnectionRepository, DuckDBStorageConnectionRepository
from .api_connection import ApiConnectionProvider, DuckDBApiConnectionProvider, PostgresDuckDBApiConnectionProvider
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
    "PostgresOperationsMetadataReader",
    "PublicationRepositoryFactory",
    "DuckDBPublicationRepositoryFactory",
    "PublicationStatusReader",
    "DuckDBPublicationStatusReader",
    "PostgresPublicationStatusReader",
    "PostgresPublicationBackend",
    "PostgresPublicationBackendFactory",
    "AnalysisActivationRepository",
    "DuckDBAnalysisActivationRepository",
    "PostgresAnalysisActivationRepository",
    "HistoryJobRepository",
    "HistoryJobStore",
    "DuckDBHistoryJobRepository",
    "DuckDBHistoryJobStore",
    "PostgresHistoryJobRepository",
    "PostgresPublicationWriter",
    "IncrementalWriterRepository",
    "DuckDBIncrementalWriterRepository",
    "ResearchBuilderRepository",
    "DuckDBResearchBuilderRepository",
    "BackupRepository",
    "DuckDBBackupRepository",
    "BackupCatalogRepository",
    "DuckDBBackupCatalogRepository",
    "PostgresBackupCatalogRepository",
    "StorageConnectionRepository",
    "DuckDBStorageConnectionRepository",
    "ApiConnectionProvider",
    "DuckDBApiConnectionProvider",
    "PostgresDuckDBApiConnectionProvider",
    "ArtifactCatalogError",
    "PostgresArtifactCatalog",
    "AdapterHttpGateway",
    "BackendRepositoryProvider",
    "RepositoryUnavailable",
]
