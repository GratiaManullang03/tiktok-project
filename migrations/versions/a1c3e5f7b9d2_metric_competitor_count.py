"""add hpm_competitor_count + tsj_limit, widen hpm_revenue, drop never-populated metric columns

Revision ID: a1c3e5f7b9d2
Revises: 899b91a6cc96
Create Date: 2026-09-24 10:00:00

hpm_competitor_count = total Tokopedia search results for the keyword the product was
found under (market-level competition signal, replaces counting our own DB rows).
review_count / commission_rate / video_count were never filled - the Tokopedia search
API doesn't expose them. hpm_revenue (price x lifetime units sold) overflowed Numeric(14,2)
(~1e12) for expensive best-sellers. tsj_limit lets scripts/rescrape.py reuse each keyword's limit.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1c3e5f7b9d2'
down_revision: Union[str, Sequence[str], None] = '899b91a6cc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "tiktok"
TABLE = "his_product_metric"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("hpm_competitor_count", sa.Integer(), nullable=True), schema=SCHEMA)
    op.drop_column(TABLE, "hpm_review_count", schema=SCHEMA)
    op.drop_column(TABLE, "hpm_commission_rate", schema=SCHEMA)
    op.drop_column(TABLE, "hpm_video_count", schema=SCHEMA)
    op.alter_column(TABLE, "hpm_revenue", type_=sa.Numeric(18, 2), schema=SCHEMA)
    op.add_column("trx_scrape_job", sa.Column("tsj_limit", sa.Integer(), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("trx_scrape_job", "tsj_limit", schema=SCHEMA)
    op.alter_column(TABLE, "hpm_revenue", type_=sa.Numeric(14, 2), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("hpm_video_count", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("hpm_commission_rate", sa.Numeric(5, 4), nullable=True), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("hpm_review_count", sa.Integer(), nullable=True), schema=SCHEMA)
    op.drop_column(TABLE, "hpm_competitor_count", schema=SCHEMA)
