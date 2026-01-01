"""

"""
import mwclient
from utils import logger


def get_category_members(site: mwclient.Site, category_title: str, namespace: int = 0) -> list:
    """
    Get members of a category.

    Args:
        site: mwclient.Site object
        category_title: Title of the category
        namespace: Namespace to filter members (0 for articles)

    Returns:
        list: List of page objects that are members of the category
    """
    try:
        category = site.pages[category_title]
        # Use list comprehension for efficiency
        return list(category.members(namespace=namespace))
    except (mwclient.errors.APIError, KeyError) as e:
        logger.warning(f"Error getting category members for {category_title}: {e}")
        return []


def sub_cats_query(site: mwclient.Site, enlink: str, namespace: str="*", lllang: str="ar") -> dict[str, str]:
    # ---
    params = {
        "action": "query",
        "format": "json",
        "prop": "langlinks",
        "generator": "categorymembers",
        "utf8": 1,
        "formatversion": "2",
        "lllang": lllang,
        "lllimit": "max",
        "gcmtitle": enlink,
        "gcmprop": "title",
        "gcmnamespace": namespace,
        "gcmlimit": "max"
    }
    # ---
    logger.info(f"<<lightblue>> sub_cats_query: {enlink=}")
    # ---
    result = site.api(**params)
    # ---
    query_pages = result.get("query", {}).get("pages", {})
    # ---
    if not query_pages:
        logger.info(f"<<lightblue>> No pages found for {enlink=}")
        return {}
    # ---
    _api_result = [
        {
            "pageid": 79686347,
            "ns": 14,
            "title": "Category:January 1913 in Asia",
            "langlinks": [{"lang": "ar", "title": "تصنيف:يناير 1913 في آسيا"}]
        },
        {"pageid": 79686425, "ns": 14, "title": "Category:October 1913 in Asia"},
        {"pageid": 79796800, "ns": 14, "title": "Category:June 1913 in Asia"}
    ]
    # ---
    pages = {
        page["title"]: next(
            (ll["title"] for ll in page.get("langlinks", []) if ll["lang"] == lllang),
            None
        )
        for page in query_pages
    }
    # ---
    pages_with_ar = {k: v for k, v in pages.items() if v is not None}
    # ---
    logger.info(f"<<lightblue>> sub_cats_query: {len(pages)=}, {len(pages_with_ar)=}")
    # ---
    return pages_with_ar


def sub_cats_query_pages(
    site: mwclient.Site,
    enlink: str,
    namespace: str="*",
    lllang: str="ar",
) -> dict[mwclient.page.Page, str]:
    pages_with_ar = sub_cats_query(site, enlink, namespace, lllang)
    page_objects = {site.pages[title]: lang_title for title, lang_title in pages_with_ar.items()}
    return page_objects


def get_interwiki_link(page, target_lang):
    """
    Get interwiki link from a page to a target language.

    Args:
        page: mwclient.Page object
        target_lang: Target language code (e.g., 'en')

    Returns:
        str or None: Title of the page in target language, or None if not found
    """
    try:
        langlinks = page.langlinks()
        for lang, title in langlinks:
            if lang == target_lang:
                return title
    except (mwclient.errors.APIError, AttributeError) as e:
        logger.warning(f"Error getting interwiki link for {page.name}: {e}")

    return None


def get_category_members_pages(
    site: mwclient.Site,
    category_title: str,
    namespace: int = 0,
    lllang: str="ar",
) -> dict[mwclient.page.Page, str]:
    members = get_category_members(site, category_title, namespace)
    data = {}

    for member in members:
        lang_title = get_interwiki_link(member, lllang)
        if lang_title:
            data[site.pages[member.name]] = lang_title

    return data
