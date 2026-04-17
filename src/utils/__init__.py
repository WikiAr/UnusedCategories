
# Text utilities
from .text_utils import (
    _build_category_pattern,
    category_in_text,
    en_page_has_category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category,
    has_ar_category_redirect_template,
)

# Configuration
from .config import (
    BotConfig,
    Credentials,
    ApprovalDecision,
    LogLevel,
    get_default_config,
    load_config_from_env,
    DEFAULT_CATEGORY_LIMIT,
    DEFAULT_EDIT_SUMMARY,
    DEFAULT_RATE_LIMIT,
)

# Exceptions
from .exceptions import (
    BotError,
    ConfigurationError,
    CredentialError,
    APIError,
    RateLimitError,
    ConnectionError,
    ProcessingError,
    CategoryProcessingError,
    PageProcessingError,
    EditError,
    ValidationError,
)

# Rate limiting
from .rate_limiter import (
    SimpleRateLimiter,
    TokenBucketRateLimiter,
    AdaptiveRateLimiter,
    create_rate_limiter,
    DEFAULT_CALLS_PER_SECOND,
)

# Types
from .types import (
    # Type aliases
    LanguageCode,
    CategoryTitle,
    PageTitle,
    NamespaceId,
    # Type variables
    T,
    # TypedDict classes
    CategoryInfo,
    QueryPageResult,
    LangLink,
    PageInfo,
    EditResult,
    CategoryProcessingResult,
    # Protocols
    PageAccessor,
    MediaWikiPage,
    MediaWikiSite,
    # Helper functions
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
