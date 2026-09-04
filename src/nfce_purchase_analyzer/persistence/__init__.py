"""Local persistence layer for the NFC-e analyzer core."""

from nfce_purchase_analyzer.persistence.categories import CategoryRepository
from nfce_purchase_analyzer.persistence.import_service import (
    DuplicateImportError,
    ImportResult,
    confirm_import,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.products import ProductRepository
from nfce_purchase_analyzer.persistence.purchases import PurchaseRepository
from nfce_purchase_analyzer.persistence.schemas import (
    category_to_dict,
    dict_to_category,
    dict_to_product,
    dict_to_purchase,
    dict_to_purchase_item,
    dict_to_store,
    product_to_dict,
    purchase_item_to_dict,
    purchase_to_dict,
    read_json,
    store_to_dict,
    write_json,
)
from nfce_purchase_analyzer.persistence.stores import StoreRepository

__all__ = [
    "CategoryRepository",
    "DuplicateImportError",
    "ImportResult",
    "ProductRepository",
    "PurchaseRepository",
    "StorageLayout",
    "StoreRepository",
    "category_to_dict",
    "confirm_import",
    "dict_to_category",
    "dict_to_product",
    "dict_to_purchase",
    "dict_to_purchase_item",
    "dict_to_store",
    "product_to_dict",
    "purchase_item_to_dict",
    "purchase_to_dict",
    "read_json",
    "store_to_dict",
    "write_json",
]
