from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.CatalogDAO import CatalogDAO
from schemas.catalog import CategoryRead, ProductRead, ProductVariantRead

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog_dao(session: AsyncSession = Depends(get_session)) -> CatalogDAO:
    return CatalogDAO(session)


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(dao: CatalogDAO = Depends(get_catalog_dao)):
    return await dao.list_categories()


@router.get("/products", response_model=list[ProductRead])
async def list_products(dao: CatalogDAO = Depends(get_catalog_dao)):
    return await dao.list_products()


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    dao: CatalogDAO = Depends(get_catalog_dao),
):
    product = await dao.get_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product

@router.get("/internal/variants/{variant_id}", response_model=ProductVariantRead)
async def get_variant_internal(
    variant_id: int,
    dao: CatalogDAO = Depends(get_catalog_dao),
):
    variant = await dao.get_product_variant(variant_id)
    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )
    return variant