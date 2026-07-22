"""
Type Definitions for Wikipedia Bot Applications.

This module provides type definitions, protocols, and type aliases used
throughout the Unused Categories Bot codebase. These definitions enable
better static analysis, IDE support, and runtime type checking.

The module uses Protocol classes from typing to define interfaces that
objects must implement, enabling duck typing while maintaining type safety.

Example:
    Type checking with protocols::

        from utils.types import MediaWikiPage, is_valid_page

        def process_page(page: MediaWikiPage) -> str:
            if is_valid_page(page):
                return page.text()
            return ""

    Using typed dictionaries::

        from utils.types import CategoryInfo, QueryPageResult

        def parse_category(data: dict) -> CategoryInfo:
            return {
                "size": data.get("size", 0),
                "pages": data.get("pages", 0),
                "hidden": data.get("hidden", False),
            }

Notes:
    - All protocols are runtime_checkable for use with isinstance()
    - Type aliases are provided for common string types (titles, language codes)
    - TypedDict classes define expected API response structures

"""

from __future__ import annotations

from typing import (
    Any,
    Literal,
    Protocol,
    TypedDict,
    TypeVar,
    runtime_checkable,
)

# =============================================================================
# Type Aliases
# =============================================================================

# Language code type (e.g., 'ar', 'en', 'fr')
LanguageCode = str

# Category title with namespace prefix (e.g., "تصنيف:علوم", "Category:Science")
CategoryTitle = str

# Page title in any namespace
PageTitle = str

# Namespace ID type (-1 for special, 0 for main, 14 for categories, etc.)
NamespaceId = int


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


# =============================================================================
# API Response TypedDict Classes
# =============================================================================


class CategoryInfo(TypedDict, total=False):
    """
    Category information from the MediaWiki API categoryinfo property.

    This TypedDict represents the structure returned by the API when
    querying category information with prop=categoryinfo.

    Attributes:
        size: Total size of all pages in the category (in bytes).
        pages: Number of pages (ns 0) in the category.
        files: Number of files (ns 6) in the category.
        subcats: Number of subcategories (ns 14) in the category.
        hidden: Whether the category is hidden (marked with __HIDDENCAT__).

    Example:
        API response structure::

            {
                "categoryinfo": {
                    "size": 12345,
                    "pages": 100,
                    "files": 5,
                    "subcats": 10,
                    "hidden": false
                }
            }

    See Also:
        https://www.mediawiki.org/wiki/API:Categoryinfo

    """

    size: int
    pages: int
    files: int
    subcats: int
    hidden: bool


class QueryPageResult(TypedDict):
    """
    Result item from the querypage MediaWiki API.

    This TypedDict represents individual items returned when querying
    special pages like Special:UnusedCategories via the querypage API.

    Attributes:
        title: Full page title including namespace prefix.
        ns: Namespace ID (14 for categories).
        value: Additional value specific to the query type
            (e.g., timestamp for unused categories).

    Example:
        API response structure::

            {
                "title": "تصنيف:تاريخ",
                "ns": 14,
                "value": "20240101000000"
            }

    """

    title: str
    ns: int
    value: str


class LangLink(TypedDict):
    """
    Language link from the MediaWiki API langlinks property.

    Attributes:
        lang: Language code of the target wiki (e.g., 'ar', 'en').
        title: Title of the corresponding page in the target language.
        autonym: Native name of the language (optional).

    """

    lang: str
    title: str


class PageInfo(TypedDict, total=False):
    """
    Page information from the MediaWiki API.

    Attributes:
        pageid: Page ID (integer), may be 0 for missing pages.
        title: Page title.
        ns: Namespace ID.
        langlinks: List of language links (present when prop=langlinks).
        categoryinfo: Category information (present for category pages).
        redirect: Present if page is a redirect.
        missing: Present if page doesn't exist.
        invalid: Present if title is invalid.

    """

    pageid: int
    title: str
    ns: int
    langlinks: list[LangLink]
    categoryinfo: CategoryInfo
    redirect: str
    missing: str
    invalid: str


class APIQueryResponse(TypedDict, total=False):
    """
    Structure of the 'query' section in API responses.

    Attributes:
        pages: Dictionary of page ID to page info (when using titles=).
        querypage: Results from querypage queries.
        continue_: Continue token for pagination.

    """

    pages: dict[str, PageInfo]
    querypage: dict[str, Any]


class APIResponse(TypedDict, total=False):
    """
    Top-level MediaWiki API response structure.

    Attributes:
        query: Query results (present for action=query).
        error: Error information (present on error).
        warnings: Warning messages.
        continue_: Continue token for pagination.

    """

    query: APIQueryResponse
    error: dict[str, Any]
    warnings: dict[str, Any]


# =============================================================================
# Protocol Classes
# =============================================================================


@runtime_checkable
class PageAccessor(Protocol):
    """
    Protocol for accessing wiki pages by title.

    This protocol defines the interface for accessing page objects from
    a wiki site. It's typically implemented by the `site.pages` attribute
    of mwclient.Site objects.

    Methods:
        __getitem__: Get a page object by title.

    Example:
        >>> pages: PageAccessor = site.pages
        >>> page = pages["Category:Science"]
        >>> print(page.name)

    """

    def __getitem__(self, title: str) -> MediaWikiPage:
        """
        Get a page object by title.

        Args:
            title: The page title, may include namespace prefix.

        Returns:
            A MediaWikiPage protocol-compliant object.

        Note:
            The returned page object is created lazily and may not
            exist on the wiki. Check page.exists() if needed.

        """
        ...


@runtime_checkable
class MediaWikiPage(Protocol):
    """
    Protocol defining the interface for MediaWiki page objects.

    This protocol defines the minimum interface that page objects must
    implement to be used with the bot. It's designed to be compatible
    with mwclient.page.Page objects while allowing for mock implementations.

    Attributes:
        name: The full page title including namespace prefix.
        namespace: The namespace ID of the page.
        site: The site object this page belongs to.

    Methods:
        text: Get the page content.
        save: Save new content to the page.
        redirects_to: Get redirect target if page is a redirect.
        langlinks: Get interwiki language links.

    Example:
        >>> def process_page(page: MediaWikiPage) -> bool:
        ...     if page.redirects_to() is not None:
        ...         return False  # Skip redirects
        ...     content = page.text()
        ...     page.save(content + "\\n[[Category:New]]", summary="Bot edit")
        ...     return True

    Note:
        All methods that make API calls may raise mwclient.errors.APIError
        or subclasses on failure.

    """

    name: str
    namespace: int
    site: MediaWikiSite

    def text(self) -> str:
        """
        Get the current content of the page.

        Returns:
            The page content as a string (wikitext format).

        Raises:
            mwclient.errors.APIError: If the API request fails.

        """
        ...

    def save(
        self,
        text: str,
        *,
        summary: str,
        minor: bool = False,
        bot: bool = True,
    ) -> dict[str, Any]:
        """
        Save new content to the page.

        Args:
            text: The new page content (wikitext format).
            summary: Edit summary for the change.
            minor: Whether to mark the edit as minor. Defaults to False.
            bot: Whether to mark the edit as a bot edit. Defaults to True.

        Returns:
            API response dictionary containing edit result.

        Raises:
            mwclient.errors.APIError: If the API request fails.
            mwclient.errors.EditError: If the edit cannot be performed.
            mwclient.errors.ProtectedPageError: If the page is protected.

        """
        ...

    def redirects_to(self) -> str | None:
        """
        Get the redirect target if this page is a redirect.

        Returns:
            The title of the redirect target, or None if the page
            is not a redirect.

        Raises:
            mwclient.errors.APIError: If the API request fails.

        """
        ...

    def langlinks(self) -> list[tuple[str, str]]:
        """
        Get interwiki language links from this page.

        Returns:
            List of (language_code, page_title) tuples representing
            the language links from this page to other wikis.

        Raises:
            mwclient.errors.APIError: If the API request fails.

        Example:
            >>> for lang, title in page.langlinks():
            ...     if lang == 'en':
            ...         print(f"English: {title}")

        """
        ...


@runtime_checkable
class MediaWikiSite(Protocol):
    """
    Protocol defining the interface for MediaWiki site connections.

    This protocol defines the minimum interface that site objects must
    implement to be used with the bot. It's designed to be compatible
    with mwclient.Site objects while allowing for mock implementations.

    Attributes:
        pages: Page accessor for creating page objects.

    Methods:
        get: Perform a GET API request.
        api: Perform a generic API request.
        login: Authenticate with the site.

    Example:
        >>> def connect(url: str) -> MediaWikiSite:
        ...     site = mwclient.Site(url, scheme='https')
        ...     return site

    Note:
        All methods that make API calls may raise mwclient.errors.APIError
        or subclasses on failure.

    """

    @property
    def pages(self) -> PageAccessor:
        """Get page accessor for creating page objects."""
        ...

    def get(
        self,
        action: Literal["query"],
        **kwargs: Any,
    ) -> APIResponse:
        """
        Perform a GET API request.

        Args:
            action: The API action to perform (typically 'query').
            **kwargs: Additional API parameters.

        Returns:
            Parsed API response as a dictionary.

        Raises:
            mwclient.errors.APIError: If the API request fails.

        """
        ...

    def api(self, **kwargs: Any) -> APIResponse:
        """
        Perform a generic API request.

        This method allows making arbitrary API calls with full control
        over parameters. It's useful for API features not covered by
        convenience methods.

        Args:
            **kwargs: API parameters as keyword arguments.

        Returns:
            Parsed API response as a dictionary.

        Raises:
            mwclient.errors.APIError: If the API request fails.

        Example:
            >>> result = site.api(
            ...     action='query',
            ...     prop='categoryinfo',
            ...     titles='Category:Science'
            ... )

        """
        ...

    def login(self, username: str, password: str) -> None:
        """
        Authenticate with the site.

        Args:
            username: The account username.
            password: The account password.

        Raises:
            mwclient.errors.LoginError: If authentication fails.
            mwclient.errors.APIError: If the API request fails.

        """
        ...


# =============================================================================
# Result Types
# =============================================================================


class EditResult(TypedDict):
    """
    Result of an edit operation.

    Attributes:
        success: Whether the edit was successful.
        page_title: The title of the edited page.
        old_revision: The revision ID before the edit.
        new_revision: The revision ID after the edit.
        timestamp: Timestamp of the edit.
        message: Optional message about the result.

    """

    success: bool
    page_title: str
    old_revision: int | None
    new_revision: int | None
    timestamp: str
    message: str | None


class CategoryProcessingResult(TypedDict):
    """
    Result of processing a single category.

    Attributes:
        category: The category name that was processed.
        success: Whether processing completed without errors.
        edits_made: Number of successful edits made.
        pages_checked: Number of pages examined.
        pages_skipped: Number of pages skipped (already had category, etc.).
        errors: List of error messages encountered.
        skipped_reason: Reason the category was skipped (if applicable).

    """

    category: str
    success: bool
    edits_made: int
    pages_checked: int
    pages_skipped: int
    errors: list[str]
    skipped_reason: str | None


# =============================================================================
# Union Types
# =============================================================================

# Note: For a generic Result type, use the following pattern in your code:
# Result = Union[Tuple[T, None], Tuple[None, Exception]]
# This is not defined here because Python doesn't support generic aliases at runtime.


# =============================================================================
# Helper Functions
# =============================================================================


def is_valid_page(obj: Any) -> bool:
    """
    Check if an object implements the MediaWikiPage protocol.

    This function performs a runtime check to verify that an object
    has all required attributes and methods of the MediaWikiPage protocol.

    Args:
        obj: The object to check.

    Returns:
        True if the object is a valid MediaWikiPage, False otherwise.

    Example:
        >>> page = site.pages["Test"]
        >>> if is_valid_page(page):
        ...     content = page.text()

    Note:
        This check is performed at runtime and may not catch all
        type incompatibilities. For static type checking, use
        isinstance() with the protocol class directly.

    """
    if not isinstance(obj, MediaWikiPage):
        return False

    required_attrs = ("name", "namespace", "site")
    required_methods = ("text", "save", "redirects_to", "langlinks")

    for attr in required_attrs:
        if not hasattr(obj, attr):
            return False

    for method in required_methods:
        if not callable(getattr(obj, method, None)):
            return False

    return True


def is_valid_site(obj: Any) -> bool:
    """
    Check if an object implements the MediaWikiSite protocol.

    Args:
        obj: The object to check.

    Returns:
        True if the object is a valid MediaWikiSite, False otherwise.

    """
    if not isinstance(obj, MediaWikiSite):
        return False

    required_methods = ("get", "api", "login")

    for method in required_methods:
        if not callable(getattr(obj, method, None)):
            return False

    if not hasattr(obj, "pages"):
        return False

    return True


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Type aliases
    "LanguageCode",
    "CategoryTitle",
    "PageTitle",
    "NamespaceId",
    # Type variables
    "T",
    "T_co",
    "T_contra",
    # TypedDict classes
    "CategoryInfo",
    "QueryPageResult",
    "LangLink",
    "PageInfo",
    "APIQueryResponse",
    "APIResponse",
    "EditResult",
    "CategoryProcessingResult",
    # Protocols
    "PageAccessor",
    "MediaWikiPage",
    "MediaWikiSite",
    # Helper functions
    "is_valid_page",
    "is_valid_site",
]
