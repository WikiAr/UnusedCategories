# Text utilities
# Configuration
from .config import (
    DEFAULT_CATEGORY_LIMIT,
    DEFAULT_EDIT_SUMMARY,
    DEFAULT_RATE_LIMIT,
    ApprovalDecision,
    BotConfig,
    Credentials,
    LogLevel,
    get_default_config,
    load_config_from_env,
)

# Exceptions
from .exceptions import (
    APIError,
    BotError,
    CategoryProcessingError,
    ConfigurationError,
    ConnectionError,
    CredentialError,
    EditError,
    PageProcessingError,
    ProcessingError,
    RateLimitError,
    ValidationError,
)

# Rate limiting
from .rate_limiter import (
    DEFAULT_CALLS_PER_SECOND,
    AdaptiveRateLimiter,
    SimpleRateLimiter,
    TokenBucketRateLimiter,
    create_rate_limiter,
)
from .text_utils import (
    _build_category_pattern,
    category_in_text,
    en_page_has_category_in_text,
    has_ar_category_redirect_template,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category,
)

# Types
from .types import (  # Type aliases; Type variables; TypedDict classes; Protocols; Helper functions
    CategoryInfo,
    CategoryProcessingResult,
    CategoryTitle,
    EditResult,
    LangLink,
    LanguageCode,
    MediaWikiPage,
    MediaWikiSite,
    NamespaceId,
    PageAccessor,
    PageInfo,
    PageTitle,
    QueryPageResult,
    T,
    is_valid_page,
    is_valid_site,
)

__all__ = [
    "_build_category_pattern",
    "category_in_text",
    "en_page_has_category_in_text",
    "is_ar_stub_or_maintenance_category",
    "is_en_stub_or_maintenance_category",
    "has_ar_category_redirect_template",
    "has_ar_category_redirect_template",
    # Configuration
    "BotConfig",
    "Credentials",
    "ApprovalDecision",
    "LogLevel",
    "get_default_config",
    "load_config_from_env",
    "DEFAULT_CATEGORY_LIMIT",
    "DEFAULT_EDIT_SUMMARY",
    "DEFAULT_RATE_LIMIT",
    # Exceptions
    "BotError",
    "ConfigurationError",
    "CredentialError",
    "APIError",
    "RateLimitError",
    "ConnectionError",
    "ProcessingError",
    "CategoryProcessingError",
    "PageProcessingError",
    "EditError",
    "ValidationError",
    # Rate limiting
    "SimpleRateLimiter",
    "TokenBucketRateLimiter",
    "AdaptiveRateLimiter",
    "create_rate_limiter",
    "DEFAULT_CALLS_PER_SECOND",
    # Types
    "LanguageCode",
    "CategoryTitle",
    "PageTitle",
    "NamespaceId",
    "T",
    "CategoryInfo",
    "QueryPageResult",
    "LangLink",
    "PageInfo",
    "EditResult",
    "CategoryProcessingResult",
    "PageAccessor",
    "MediaWikiPage",
    "MediaWikiSite",
    "is_valid_page",
    "is_valid_site",
]
