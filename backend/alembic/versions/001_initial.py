"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID_COL = sa.CHAR(32)


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("default_currency", sa.String(10), nullable=False, server_default="KRW"),
        sa.Column("salary_day", sa.Integer, nullable=False, server_default="25"),
        sa.Column("notification_preferences", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- assets ---
    op.create_table(
        "assets",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("interest_rate", sa.Float, nullable=True),
        sa.Column("interest_type", sa.String(20), nullable=True),
        sa.Column("principal", sa.Float, nullable=True),
        sa.Column("monthly_amount", sa.Float, nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("maturity_date", sa.Date, nullable=True),
        sa.Column("tax_rate", sa.Float, nullable=True),
        sa.Column("bank_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_assets_user_id", "assets", ["user_id"])

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", UUID_COL, sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="KRW"),
        sa.Column("exchange_rate", sa.Float, nullable=True),
        sa.Column("fee", sa.Float, nullable=False, server_default="0"),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("transacted_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_asset_id", "transactions", ["asset_id"])

    # --- budget_categories ---
    op.create_table(
        "budget_categories",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("monthly_budget", sa.Float, nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_budget_categories_user_id", "budget_categories", ["user_id"])

    # --- expenses ---
    op.create_table(
        "expenses",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID_COL, sa.ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("spent_at", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_expenses_user_spent", "expenses", ["user_id", "spent_at"])
    op.create_index("ix_expenses_user_category_spent", "expenses", ["user_id", "category_id", "spent_at"])

    # --- fixed_expenses ---
    op.create_table(
        "fixed_expenses",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID_COL, sa.ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("payment_day", sa.Integer, nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- installments ---
    op.create_table(
        "installments",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID_COL, sa.ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("total_amount", sa.Float, nullable=False),
        sa.Column("monthly_amount", sa.Float, nullable=False),
        sa.Column("payment_day", sa.Integer, nullable=False),
        sa.Column("total_installments", sa.Integer, nullable=False),
        sa.Column("paid_installments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- budget_carryover_settings ---
    op.create_table(
        "budget_carryover_settings",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID_COL, sa.ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("carryover_type", sa.String(20), nullable=False, server_default="expire"),
        sa.Column("carryover_limit", sa.Float, nullable=True),
        sa.Column("target_asset_id", UUID_COL, nullable=True),
        sa.Column("target_savings_name", sa.String(200), nullable=True),
        sa.Column("target_annual_rate", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("uq_carryover_user_category", "budget_carryover_settings", ["user_id", "category_id"], unique=True)

    # --- budget_carryover_logs ---
    op.create_table(
        "budget_carryover_logs",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID_COL, sa.ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("budget_period_start", sa.Date, nullable=False),
        sa.Column("budget_period_end", sa.Date, nullable=False),
        sa.Column("carryover_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("target_description", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # --- incomes ---
    op.create_table(
        "incomes",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("recurring_day", sa.Integer, nullable=True),
        sa.Column("received_at", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_incomes_user_id", "incomes", ["user_id"])

    # --- asset_snapshots ---
    op.create_table(
        "asset_snapshots",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("total_krw", sa.Float, nullable=False),
        sa.Column("breakdown", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_snapshots_user_date", "asset_snapshots", ["user_id", "snapshot_date"], unique=True)

    # --- portfolio_targets ---
    op.create_table(
        "portfolio_targets",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("target_ratio", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("uq_portfolio_user_asset_type", "portfolio_targets", ["user_id", "asset_type"], unique=True)

    # --- rebalancing_alerts ---
    op.create_table(
        "rebalancing_alerts",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("deviations", sa.JSON, nullable=False),
        sa.Column("suggestion", sa.JSON, nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- goal_assets ---
    op.create_table(
        "goal_assets",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("target_amount", sa.Float, nullable=False),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- api_keys ---
    op.create_table(
        "api_keys",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("uq_api_key_user_service", "api_keys", ["user_id", "service"], unique=True)

    # --- llm_settings ---
    op.create_table(
        "llm_settings",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("default_model", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("inference_model", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("user_id", UUID_COL, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="새 대화"),
        sa.Column("agent_state", sa.JSON, nullable=True),
        sa.Column("context_snapshot", sa.JSON, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("conversation_id", UUID_COL, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # --- news_articles ---
    op.create_table(
        "news_articles",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("external_id", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("link", sa.String(1000), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_icon", sa.String(500), nullable=True),
        sa.Column("snippet", sa.Text, nullable=True),
        sa.Column("thumbnail", sa.String(500), nullable=True),
        sa.Column("published_at", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("related_asset", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("keywords", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("processed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_news_category_created", "news_articles", ["category", "created_at"])
    op.create_index("ix_news_external_id", "news_articles", ["external_id"])

    # --- news_clusters ---
    op.create_table(
        "news_clusters",
        sa.Column("id", UUID_COL, primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False, server_default="neutral"),
        sa.Column("avg_sentiment_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("article_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("article_ids", sa.Text, nullable=False),
        sa.Column("keywords", sa.Text, nullable=False),
        sa.Column("importance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_clusters_created", "news_clusters", ["created_at"])
    op.create_index("ix_clusters_category", "news_clusters", ["category"])


def downgrade() -> None:
    op.drop_table("news_clusters")
    op.drop_table("news_articles")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("llm_settings")
    op.drop_table("api_keys")
    op.drop_table("goal_assets")
    op.drop_table("rebalancing_alerts")
    op.drop_table("portfolio_targets")
    op.drop_table("asset_snapshots")
    op.drop_table("incomes")
    op.drop_table("budget_carryover_logs")
    op.drop_table("budget_carryover_settings")
    op.drop_table("installments")
    op.drop_table("fixed_expenses")
    op.drop_table("expenses")
    op.drop_table("budget_categories")
    op.drop_table("transactions")
    op.drop_table("assets")
    op.drop_table("users")
