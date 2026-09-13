"""create initial tables

Revision ID: 899b91a6cc96
Revises:
Create Date: 2026-09-13 09:44:03.834737

Naming follows docs/ERDRULES.md: mst_/his_/trx_ table prefixes, primary keys
as table-abbreviation + _id, foreign keys as <own_prefix>_<referenced_pk>,
and explicit pk_/fk_/uq_/idx_ constraint names.

No created_by/updated_by/deleted_by columns - this is a single-user personal
tool with no account system, so there's no real actor identity to record.
created_at/updated_at/is_deleted/deleted_at are kept since they don't require one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '899b91a6cc96'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "tiktok"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "mst_product",
        sa.Column("mp_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mp_external_id", sa.String(), nullable=False),
        sa.Column("mp_name", sa.String(), nullable=False),
        sa.Column("mp_category", sa.String(), nullable=True),
        sa.Column("mp_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("mp_currency", sa.String(), nullable=True),
        sa.Column("mp_shop_name", sa.String(), nullable=True),
        sa.Column("mp_shop_id", sa.String(), nullable=True),
        sa.Column("mp_image_url", sa.String(), nullable=True),
        sa.Column("mp_product_url", sa.String(), nullable=True),
        sa.Column("mp_source", sa.String(), nullable=False),
        sa.Column("mp_last_scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("mp_id", name="pk_mst_product"),
        sa.UniqueConstraint("mp_external_id", name="uq_mp_external_id"),
        schema=SCHEMA,
    )
    op.create_index("idx_mp_category", "mst_product", ["mp_category"], schema=SCHEMA)

    op.create_table(
        "his_product_metric",
        sa.Column("hpm_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("hpm_mp_id", sa.BigInteger(), nullable=False),
        sa.Column("hpm_units_sold", sa.Integer(), nullable=True),
        sa.Column("hpm_revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("hpm_rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("hpm_review_count", sa.Integer(), nullable=True),
        sa.Column("hpm_commission_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("hpm_video_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("hpm_id", name="pk_his_product_metric"),
        sa.ForeignKeyConstraint(
            ["hpm_mp_id"], [f"{SCHEMA}.mst_product.mp_id"], name="fk_his_product_metric_product"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_hpm_mp_id", "his_product_metric", ["hpm_mp_id"], schema=SCHEMA)

    op.create_table(
        "his_product_score",
        sa.Column("hps_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("hps_mp_id", sa.BigInteger(), nullable=False),
        sa.Column("hps_total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("hps_sales_velocity_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("hps_growth_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("hps_rating_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("hps_competition_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("hps_id", name="pk_his_product_score"),
        sa.ForeignKeyConstraint(
            ["hps_mp_id"], [f"{SCHEMA}.mst_product.mp_id"], name="fk_his_product_score_product"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_hps_mp_id", "his_product_score", ["hps_mp_id"], schema=SCHEMA)

    op.create_table(
        "his_product_analysis",
        sa.Column("hpa_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("hpa_mp_id", sa.BigInteger(), nullable=False),
        sa.Column("hpa_llm_model", sa.String(), nullable=False),
        sa.Column("hpa_summary", sa.Text(), nullable=False),
        sa.Column("hpa_strengths", postgresql.JSONB(), nullable=False),
        sa.Column("hpa_risks", postgresql.JSONB(), nullable=False),
        sa.Column("hpa_target_audience", sa.Text(), nullable=False),
        sa.Column("hpa_marketing_angle", sa.Text(), nullable=False),
        sa.Column("hpa_verdict", sa.String(), nullable=False),
        sa.Column("hpa_raw_response", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("hpa_id", name="pk_his_product_analysis"),
        sa.ForeignKeyConstraint(
            ["hpa_mp_id"], [f"{SCHEMA}.mst_product.mp_id"], name="fk_his_product_analysis_product"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_hpa_mp_id", "his_product_analysis", ["hpa_mp_id"], schema=SCHEMA)

    op.create_table(
        "trx_scrape_job",
        sa.Column("tsj_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tsj_keyword", sa.String(), nullable=False),
        sa.Column("tsj_source", sa.String(), nullable=False),
        sa.Column("tsj_status", sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("tsj_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tsj_products_found", sa.Integer(), nullable=True),
        sa.Column("tsj_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("tsj_id", name="pk_trx_scrape_job"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("trx_scrape_job", schema=SCHEMA)
    op.drop_table("his_product_analysis", schema=SCHEMA)
    op.drop_table("his_product_score", schema=SCHEMA)
    op.drop_table("his_product_metric", schema=SCHEMA)
    op.drop_table("mst_product", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
