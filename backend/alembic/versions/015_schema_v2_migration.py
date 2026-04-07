"""Schema v2 migration: accounts, securities, entries, categories, recurring_schedules, account_snapshots

Migrates from old schema (Asset + Transaction/Income/Expense) to new schema
(Account + Security + unified Entry ledger).

Revision ID: 015_schema_v2
Revises: 014_recurring_income
Create Date: 2026-04-07
"""

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "015_schema_v2"
down_revision = "014_recurring_income"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Helper: consistent UUID column definition (matches later migration style)
# ---------------------------------------------------------------------------
UUID_TYPE = sa.Uuid()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    """Generate a new UUID string suitable for MySQL Uuid column."""
    return str(uuid.uuid4())


# ===================================================================
# UPGRADE
# ===================================================================

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Phase 1: Create new tables
    # ------------------------------------------------------------------
    _create_accounts_table()
    _create_securities_table()
    _create_security_prices_table()
    _create_categories_table()
    _create_entry_groups_table()
    _create_entries_table()
    _create_recurring_schedules_table()
    _create_account_snapshots_table()

    # ------------------------------------------------------------------
    # Phase 2: Migrate data
    # ------------------------------------------------------------------
    conn = op.get_bind()
    _migrate_data(conn)

    # ------------------------------------------------------------------
    # Phase 3: Drop old tables (reverse FK order)
    # ------------------------------------------------------------------
    _drop_old_tables()


# ===================================================================
# TABLE CREATION FUNCTIONS
# ===================================================================

def _create_accounts_table():
    op.create_table(
        "accounts",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column(
            "account_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KRW"),
        sa.Column("institution", sa.String(50), nullable=True),
        sa.Column("interest_rate", sa.Numeric(5, 3), nullable=True),
        sa.Column(
            "interest_type",
            sa.String(20),
            nullable=True,
        ),
        sa.Column("monthly_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("maturity_date", sa.Date, nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 3), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])


def _create_securities_table():
    op.create_table(
        "securities",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "asset_class",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "data_source",
            sa.String(20),
            nullable=False,
            server_default="yahoo",
        ),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_securities_symbol", "securities", ["symbol"])
    op.create_unique_constraint("uq_security_symbol_source", "securities", ["symbol", "data_source"])


def _create_security_prices_table():
    op.create_table(
        "security_prices",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column(
            "security_id", UUID_TYPE,
            sa.ForeignKey("securities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price_date", sa.Date, nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_security_prices_security_id", "security_prices", ["security_id"])
    op.create_unique_constraint("uq_price_security_date", "security_prices", ["security_id", "price_date"])


def _create_categories_table():
    op.create_table(
        "categories",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column(
            "direction",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_unique_constraint("uq_category_user_direction_name", "categories", ["user_id", "direction", "name"])


def _create_entry_groups_table():
    op.create_table(
        "entry_groups",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column(
            "group_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_entry_groups_user_id", "entry_groups", ["user_id"])


def _create_entries_table():
    op.create_table(
        "entries",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column(
            "account_id", UUID_TYPE,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entry_group_id", UUID_TYPE,
            sa.ForeignKey("entry_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id", UUID_TYPE,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "security_id", UUID_TYPE,
            sa.ForeignKey("securities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KRW"),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("fee", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("exchange_rate", sa.Numeric(12, 4), nullable=True),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column(
            "recurring_schedule_id", UUID_TYPE,
            sa.ForeignKey("recurring_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("transacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_entries_user_transacted", "entries", ["user_id", "transacted_at"])
    op.create_index("ix_entries_account_transacted", "entries", ["account_id", "transacted_at"])
    op.create_index("ix_entries_account_security", "entries", ["account_id", "security_id"])
    op.create_index("ix_entries_user_category_transacted", "entries", ["user_id", "category_id", "transacted_at"])


def _create_recurring_schedules_table():
    op.create_table(
        "recurring_schedules",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column(
            "type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KRW"),
        sa.Column("schedule_day", sa.Integer, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("total_count", sa.Integer, nullable=True),
        sa.Column("executed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "source_account_id", UUID_TYPE,
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_account_id", UUID_TYPE,
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id", UUID_TYPE,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "security_id", UUID_TYPE,
            sa.ForeignKey("securities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recurring_schedules_user_id", "recurring_schedules", ["user_id"])


def _create_account_snapshots_table():
    op.create_table(
        "account_snapshots",
        sa.Column("id", UUID_TYPE, primary_key=True),
        sa.Column(
            "account_id", UUID_TYPE,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("holdings", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_account_snapshots_account_id", "account_snapshots", ["account_id"])
    op.create_index("ix_account_snapshots_user_id", "account_snapshots", ["user_id"])
    op.create_unique_constraint("uq_account_snapshot_date", "account_snapshots", ["account_id", "snapshot_date"])


# ===================================================================
# DATA MIGRATION
# ===================================================================

def _migrate_data(conn):
    """Orchestrate all data migration steps."""

    # ---------------------------------------------------------------
    # Step 0: Build old asset lookup {name -> (id, asset_type, ...)}
    # ---------------------------------------------------------------
    old_assets = conn.execute(sa.text(
        "SELECT id, user_id, asset_type, symbol, name, interest_rate, interest_type, "
        "principal, monthly_amount, start_date, maturity_date, tax_rate, bank_name, created_at "
        "FROM assets"
    )).fetchall()

    if not old_assets:
        return  # Nothing to migrate

    # Build helper maps
    # old_asset_by_id: {old_uuid: row}
    old_asset_by_id = {}
    # old_asset_by_name: {name: row}
    old_asset_by_name = {}
    for row in old_assets:
        old_asset_by_id[str(row[0])] = row
        old_asset_by_name[row[4]] = row  # name

    # Detect the user_id (single-user app from data context)
    user_id = str(old_assets[0][1])

    # ---------------------------------------------------------------
    # Step 1: Identify the "한투 원화" asset for ISA merge
    # ---------------------------------------------------------------
    hantu_won_id = None
    isa_id = None

    for row in old_assets:
        name = row[4]
        if name == "한투 원화":
            hantu_won_id = str(row[0])
        elif name == "ISA":
            isa_id = str(row[0])

    # ---------------------------------------------------------------
    # Step 2: Create accounts from non-stock/non-gold assets
    # ---------------------------------------------------------------
    # old_asset_id -> new_account_id mapping
    asset_to_account = {}

    # Also track which old asset IDs are securities (stock/gold)
    old_security_asset_ids = set()
    # old_asset_id -> new_security_id
    asset_to_security = {}

    for row in old_assets:
        asset_id_str = str(row[0])
        asset_type = row[2]  # asset_type string
        name = row[4]

        # Normalize asset_type to lowercase for comparison
        at = asset_type.lower() if isinstance(asset_type, str) else str(asset_type).lower()

        # Securities: will handle separately
        if at in ("stock_kr", "stock_us", "gold"):
            old_security_asset_ids.add(asset_id_str)
            continue

        # Skip 한투 원화 (merge into ISA)
        if name == "한투 원화":
            continue

        # Determine account_type
        if name in ("ISA",):
            account_type = "investment"
        elif name == "미래에셋":
            account_type = "investment"
        elif name == "한투 달러":
            account_type = "investment"
        elif at in ("parking",):
            account_type = "parking"
        elif at in ("savings",):
            account_type = "savings"
        elif at in ("deposit",):
            account_type = "deposit"
        else:
            # CASH_KRW default -> cash
            account_type = "cash"

        # Determine currency & name overrides
        currency = "KRW"
        acct_name = name
        if name == "한투 달러":
            acct_name = "한투증권"
            currency = "KRW"  # base currency is KRW, USD entries use entry.currency

        # Keep the same UUID as old asset for easier FK remapping
        new_account_id = asset_id_str

        conn.execute(sa.text("""
            INSERT INTO accounts (id, user_id, account_type, name, currency, institution,
                                  interest_rate, interest_type, monthly_amount,
                                  start_date, maturity_date, tax_rate,
                                  is_active, created_at, updated_at)
            VALUES (:id, :user_id, :account_type, :name, :currency, :institution,
                    :interest_rate, :interest_type, :monthly_amount,
                    :start_date, :maturity_date, :tax_rate,
                    1, :created_at, :created_at)
        """), {
            "id": new_account_id,
            "user_id": user_id,
            "account_type": account_type,
            "name": acct_name,
            "currency": currency,
            "institution": row[12],  # bank_name -> institution
            "interest_rate": row[5],
            "interest_type": str(row[6]).lower() if row[6] else None,
            "monthly_amount": row[8],
            "start_date": row[9],
            "maturity_date": row[10],
            "tax_rate": row[11],
            "created_at": row[13],
        })

        asset_to_account[asset_id_str] = new_account_id

    # 한투 원화 -> ISA remapping
    if hantu_won_id and isa_id:
        asset_to_account[hantu_won_id] = isa_id  # redirect references

    # ---------------------------------------------------------------
    # Step 3: Create securities from stock/gold assets
    # ---------------------------------------------------------------
    for row in old_assets:
        asset_id_str = str(row[0])
        asset_type = row[2]
        at = asset_type.lower() if isinstance(asset_type, str) else str(asset_type).lower()

        if at not in ("stock_kr", "stock_us", "gold"):
            continue

        # Map asset_class
        if at == "stock_kr":
            asset_class = "equity_kr"
            currency = "KRW"
        elif at == "stock_us":
            asset_class = "equity_us"
            currency = "USD"
        else:  # gold
            asset_class = "commodity"
            currency = "USD"

        new_sec_id = _uuid()
        symbol = row[3] or ""  # symbol column
        sec_name = row[4]

        conn.execute(sa.text("""
            INSERT INTO securities (id, symbol, name, currency, asset_class, data_source, created_at)
            VALUES (:id, :symbol, :name, :currency, :asset_class, 'yahoo', :created_at)
        """), {
            "id": new_sec_id,
            "symbol": symbol,
            "name": sec_name,
            "currency": currency,
            "asset_class": asset_class,
            "created_at": row[13],
        })

        asset_to_security[asset_id_str] = new_sec_id

    # ---------------------------------------------------------------
    # Step 4: Determine which investment account holds which securities
    # ---------------------------------------------------------------
    # ISA account -> TIGER S&P500
    # 한투증권 account (old 한투 달러) -> US stocks
    hantu_dollar_id = None
    for row in old_assets:
        if row[4] == "한투 달러":
            hantu_dollar_id = str(row[0])
            break

    def _get_investment_account_for_security(old_asset_name: str) -> str | None:
        """Given a security's old name, return the investment account_id it belongs to."""
        if old_asset_name == "TIGER S&P500":
            return isa_id
        # All US stocks + gold belong to 한투증권
        return hantu_dollar_id

    # ---------------------------------------------------------------
    # Step 5: Migrate budget_categories -> categories
    # ---------------------------------------------------------------
    conn.execute(sa.text("""
        INSERT INTO categories (id, user_id, direction, name, icon, color, sort_order, is_active, created_at, updated_at)
        SELECT id, user_id, 'expense', name, icon, color, sort_order, is_active, created_at, updated_at
        FROM budget_categories
    """))

    # ---------------------------------------------------------------
    # Step 6: Migrate transactions -> entries
    # ---------------------------------------------------------------
    old_txns = conn.execute(sa.text(
        "SELECT id, user_id, asset_id, type, quantity, unit_price, currency, "
        "exchange_rate, fee, source_asset_id, memo, transacted_at, created_at "
        "FROM transactions ORDER BY transacted_at"
    )).fetchall()

    for txn in old_txns:
        txn_id = str(txn[0])
        txn_user_id = str(txn[1])
        txn_asset_id = str(txn[2])
        txn_type = txn[3].lower() if isinstance(txn[3], str) else str(txn[3]).lower()
        quantity = txn[4]
        unit_price = txn[5]
        currency = str(txn[6]) if txn[6] else "KRW"
        exchange_rate = txn[7]
        fee = txn[8] or 0
        source_asset_id = str(txn[9]) if txn[9] else None
        memo = txn[10]
        transacted_at = txn[11]
        created_at = txn[12]

        if txn_type == "buy":
            # BUY transaction: asset_id is the stock/gold asset
            security_id = asset_to_security.get(txn_asset_id)

            # Find which investment account this security belongs to
            old_asset_row = old_asset_by_id.get(txn_asset_id)
            old_asset_name = old_asset_row[4] if old_asset_row else None
            account_id = _get_investment_account_for_security(old_asset_name) if old_asset_name else None

            # Fallback: use source_asset_id mapped to account
            if not account_id and source_asset_id:
                account_id = asset_to_account.get(source_asset_id)

            if not account_id:
                # Last resort: skip if we cannot determine the account
                continue

            # BUY entry: amount = -(quantity * unit_price + fee)
            total_cost = float(quantity or 0) * float(unit_price or 0) + float(fee)
            amount = -total_cost

            conn.execute(sa.text("""
                INSERT INTO entries (id, user_id, account_id, security_id, type,
                                    amount, currency, quantity, unit_price, fee,
                                    exchange_rate, memo, transacted_at, created_at)
                VALUES (:id, :user_id, :account_id, :security_id, 'buy',
                        :amount, :currency, :quantity, :unit_price, :fee,
                        :exchange_rate, :memo, :transacted_at, :created_at)
            """), {
                "id": txn_id,
                "user_id": txn_user_id,
                "account_id": account_id,
                "security_id": security_id,
                "amount": amount,
                "currency": currency,
                "quantity": quantity,
                "unit_price": unit_price,
                "fee": fee,
                "exchange_rate": exchange_rate,
                "memo": memo,
                "transacted_at": transacted_at,
                "created_at": created_at,
            })

        elif txn_type == "sell":
            # SELL: similar to buy but positive amount
            security_id = asset_to_security.get(txn_asset_id)
            old_asset_row = old_asset_by_id.get(txn_asset_id)
            old_asset_name = old_asset_row[4] if old_asset_row else None
            account_id = _get_investment_account_for_security(old_asset_name) if old_asset_name else None

            if not account_id and source_asset_id:
                account_id = asset_to_account.get(source_asset_id)
            if not account_id:
                continue

            total_proceeds = float(quantity or 0) * float(unit_price or 0) - float(fee)
            amount = total_proceeds

            conn.execute(sa.text("""
                INSERT INTO entries (id, user_id, account_id, security_id, type,
                                    amount, currency, quantity, unit_price, fee,
                                    exchange_rate, memo, transacted_at, created_at)
                VALUES (:id, :user_id, :account_id, :security_id, 'sell',
                        :amount, :currency, :quantity, :unit_price, :fee,
                        :exchange_rate, :memo, :transacted_at, :created_at)
            """), {
                "id": txn_id,
                "user_id": txn_user_id,
                "account_id": account_id,
                "security_id": security_id,
                "amount": amount,
                "currency": currency,
                "quantity": quantity,
                "unit_price": unit_price,
                "fee": fee,
                "exchange_rate": exchange_rate,
                "memo": memo,
                "transacted_at": transacted_at,
                "created_at": created_at,
            })

        elif txn_type == "deposit":
            # DEPOSIT: money coming into an account
            target_account_id = asset_to_account.get(txn_asset_id)
            source_account_id = asset_to_account.get(source_asset_id) if source_asset_id else None

            if source_asset_id and source_account_id and target_account_id:
                # Transfer pair: source -> target
                group_id = _uuid()
                conn.execute(sa.text("""
                    INSERT INTO entry_groups (id, user_id, group_type, description, created_at)
                    VALUES (:id, :user_id, 'transfer', :desc, :created_at)
                """), {
                    "id": group_id,
                    "user_id": txn_user_id,
                    "desc": memo,
                    "created_at": created_at,
                })

                deposit_amount = float(quantity or 0) * float(unit_price or 0)

                # transfer_out from source
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, entry_group_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, :group_id, 'transfer_out',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": _uuid(),
                    "user_id": txn_user_id,
                    "account_id": source_account_id,
                    "group_id": group_id,
                    "amount": -deposit_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })

                # transfer_in to target
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, entry_group_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, :group_id, 'transfer_in',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": txn_id,  # Keep original ID on the "main" entry
                    "user_id": txn_user_id,
                    "account_id": target_account_id,
                    "group_id": group_id,
                    "amount": deposit_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })
            elif target_account_id:
                # Standalone deposit (no source) -> income or adjustment
                deposit_amount = float(quantity or 0) * float(unit_price or 0)
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, 'adjustment',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": txn_id,
                    "user_id": txn_user_id,
                    "account_id": target_account_id,
                    "amount": deposit_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })

        elif txn_type == "withdraw":
            # WITHDRAW: money leaving an account
            source_account_id_mapped = asset_to_account.get(txn_asset_id)
            target_account_id_mapped = asset_to_account.get(source_asset_id) if source_asset_id else None

            # Note: in old schema, for withdraw the "asset_id" is the account being withdrawn FROM
            # and source_asset_id can be destination (confusing naming)
            if source_asset_id and target_account_id_mapped and source_account_id_mapped:
                # Transfer pair
                group_id = _uuid()
                conn.execute(sa.text("""
                    INSERT INTO entry_groups (id, user_id, group_type, description, created_at)
                    VALUES (:id, :user_id, 'transfer', :desc, :created_at)
                """), {
                    "id": group_id,
                    "user_id": txn_user_id,
                    "desc": memo,
                    "created_at": created_at,
                })

                withdraw_amount = float(quantity or 0) * float(unit_price or 0)

                # transfer_out from source (the account being withdrawn from)
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, entry_group_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, :group_id, 'transfer_out',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": txn_id,
                    "user_id": txn_user_id,
                    "account_id": source_account_id_mapped,
                    "group_id": group_id,
                    "amount": -withdraw_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })

                # transfer_in to target
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, entry_group_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, :group_id, 'transfer_in',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": _uuid(),
                    "user_id": txn_user_id,
                    "account_id": target_account_id_mapped,
                    "group_id": group_id,
                    "amount": withdraw_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })
            elif source_account_id_mapped:
                # Standalone withdraw -> expense or adjustment
                withdraw_amount = float(quantity or 0) * float(unit_price or 0)
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, type,
                                        amount, currency, memo, transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, 'adjustment',
                            :amount, :currency, :memo, :transacted_at, :created_at)
                """), {
                    "id": txn_id,
                    "user_id": txn_user_id,
                    "account_id": source_account_id_mapped,
                    "amount": -withdraw_amount,
                    "currency": currency,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })

        elif txn_type == "exchange":
            # EXCHANGE: treat as adjustment on the target account
            target_account_id = asset_to_account.get(txn_asset_id)
            if target_account_id:
                exchange_amount = float(quantity or 0) * float(unit_price or 0)
                conn.execute(sa.text("""
                    INSERT INTO entries (id, user_id, account_id, type,
                                        amount, currency, exchange_rate, memo,
                                        transacted_at, created_at)
                    VALUES (:id, :user_id, :account_id, 'adjustment',
                            :amount, :currency, :exchange_rate, :memo,
                            :transacted_at, :created_at)
                """), {
                    "id": txn_id,
                    "user_id": txn_user_id,
                    "account_id": target_account_id,
                    "amount": exchange_amount,
                    "currency": currency,
                    "exchange_rate": exchange_rate,
                    "memo": memo,
                    "transacted_at": transacted_at,
                    "created_at": created_at,
                })

    # ---------------------------------------------------------------
    # Step 7: Migrate incomes -> entries
    # ---------------------------------------------------------------
    old_incomes = conn.execute(sa.text(
        "SELECT id, user_id, type, amount, description, target_asset_id, "
        "received_at, created_at "
        "FROM incomes ORDER BY received_at"
    )).fetchall()

    for inc in old_incomes:
        inc_id = str(inc[0])
        inc_user_id = str(inc[1])
        # inc[2] = income type (salary/side/investment/other) - not used directly;
        # entry type is determined by description keywords below.
        inc_amount = float(inc[3] or 0)
        description = inc[4] or ""
        target_asset_id = str(inc[5]) if inc[5] else None
        received_at = inc[6]
        created_at = inc[7]

        # Determine entry type
        if "일일이자" in description:
            entry_type = "interest"
        elif "배당" in description:
            entry_type = "dividend"
        else:
            entry_type = "income"

        # Determine account_id
        account_id = None
        if target_asset_id:
            account_id = asset_to_account.get(target_asset_id)
        if not account_id:
            # Fallback: try to find a default account (e.g. 급여통장 for salary)
            # Use the first 'parking' or 'cash' account we created
            for old_id, new_id in asset_to_account.items():
                account_id = new_id
                break

        if not account_id:
            continue

        # received_at is a Date, need to convert to DateTime for transacted_at
        transacted_at = received_at

        conn.execute(sa.text("""
            INSERT INTO entries (id, user_id, account_id, type,
                                amount, currency, memo, transacted_at, created_at)
            VALUES (:id, :user_id, :account_id, :type,
                    :amount, 'KRW', :memo, :transacted_at, :created_at)
        """), {
            "id": inc_id,
            "user_id": inc_user_id,
            "account_id": account_id,
            "type": entry_type,
            "amount": inc_amount,  # positive for income
            "memo": description,
            "transacted_at": transacted_at,
            "created_at": created_at,
        })

    # ---------------------------------------------------------------
    # Step 8: Migrate expenses -> entries
    # ---------------------------------------------------------------
    old_expenses = conn.execute(sa.text(
        "SELECT id, user_id, category_id, amount, memo, source_asset_id, "
        "spent_at, created_at "
        "FROM expenses ORDER BY spent_at"
    )).fetchall()

    for exp in old_expenses:
        exp_id = str(exp[0])
        exp_user_id = str(exp[1])
        category_id = str(exp[2]) if exp[2] else None
        exp_amount = float(exp[3] or 0)
        memo = exp[4]
        source_asset_id = str(exp[5]) if exp[5] else None
        spent_at = exp[6]
        created_at = exp[7]

        # Determine account_id
        account_id = None
        if source_asset_id:
            account_id = asset_to_account.get(source_asset_id)
        if not account_id:
            # Fallback: first available account
            for old_id, new_id in asset_to_account.items():
                account_id = new_id
                break

        if not account_id:
            continue

        conn.execute(sa.text("""
            INSERT INTO entries (id, user_id, account_id, category_id, type,
                                amount, currency, memo, transacted_at, created_at)
            VALUES (:id, :user_id, :account_id, :category_id, 'expense',
                    :amount, 'KRW', :memo, :transacted_at, :created_at)
        """), {
            "id": exp_id,
            "user_id": exp_user_id,
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": -exp_amount,  # negative for expense
            "memo": memo,
            "transacted_at": spent_at,
            "created_at": created_at,
        })

    # ---------------------------------------------------------------
    # Step 9: Migrate fixed_expenses -> recurring_schedules (type=expense)
    # ---------------------------------------------------------------
    old_fixed = conn.execute(sa.text(
        "SELECT id, user_id, category_id, name, amount, payment_day, "
        "source_asset_id, is_active, created_at, updated_at "
        "FROM fixed_expenses"
    )).fetchall()

    for fe in old_fixed:
        fe_id = str(fe[0])
        fe_user_id = str(fe[1])
        fe_category_id = str(fe[2]) if fe[2] else None
        fe_name = fe[3]
        fe_amount = fe[4]
        fe_day = fe[5]
        fe_source = str(fe[6]) if fe[6] else None
        fe_active = fe[7]
        fe_created = fe[8]
        fe_updated = fe[9]

        source_acct = asset_to_account.get(fe_source) if fe_source else None

        conn.execute(sa.text("""
            INSERT INTO recurring_schedules
                (id, user_id, type, name, amount, currency, schedule_day,
                 start_date, source_account_id, category_id,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, 'expense', :name, :amount, 'KRW', :day,
                 :start_date, :source_account_id, :category_id,
                 :is_active, :created_at, :updated_at)
        """), {
            "id": fe_id,
            "user_id": fe_user_id,
            "name": fe_name,
            "amount": fe_amount,
            "day": fe_day,
            "start_date": fe_created,  # Use created_at as start_date approximation
            "source_account_id": source_acct,
            "category_id": fe_category_id,
            "is_active": fe_active,
            "created_at": fe_created,
            "updated_at": fe_updated,
        })

    # ---------------------------------------------------------------
    # Step 10: Migrate recurring_incomes -> recurring_schedules (type=income)
    # ---------------------------------------------------------------
    old_ri = conn.execute(sa.text(
        "SELECT id, user_id, type, amount, description, recurring_day, "
        "target_asset_id, is_active, created_at, updated_at "
        "FROM recurring_incomes"
    )).fetchall()

    for ri in old_ri:
        ri_id = str(ri[0])
        ri_user_id = str(ri[1])
        ri_name = ri[4]  # description -> name
        ri_amount = ri[3]
        ri_day = ri[5]
        ri_target = str(ri[6]) if ri[6] else None
        ri_active = ri[7]
        ri_created = ri[8]
        ri_updated = ri[9]

        target_acct = asset_to_account.get(ri_target) if ri_target else None

        conn.execute(sa.text("""
            INSERT INTO recurring_schedules
                (id, user_id, type, name, amount, currency, schedule_day,
                 start_date, target_account_id,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, 'income', :name, :amount, 'KRW', :day,
                 :start_date, :target_account_id,
                 :is_active, :created_at, :updated_at)
        """), {
            "id": ri_id,
            "user_id": ri_user_id,
            "name": ri_name,
            "amount": ri_amount,
            "day": ri_day,
            "start_date": ri_created,
            "target_account_id": target_acct,
            "is_active": ri_active,
            "created_at": ri_created,
            "updated_at": ri_updated,
        })

    # ---------------------------------------------------------------
    # Step 11: Migrate auto_transfers -> recurring_schedules (type=transfer)
    # ---------------------------------------------------------------
    old_at = conn.execute(sa.text(
        "SELECT id, user_id, source_asset_id, target_asset_id, name, amount, "
        "transfer_day, is_active, created_at "
        "FROM auto_transfers"
    )).fetchall()

    for at_row in old_at:
        at_id = str(at_row[0])
        at_user_id = str(at_row[1])
        at_source = str(at_row[2]) if at_row[2] else None
        at_target = str(at_row[3]) if at_row[3] else None
        at_name = at_row[4]
        at_amount = at_row[5]
        at_day = at_row[6]
        at_active = at_row[7]
        at_created = at_row[8]

        source_acct = asset_to_account.get(at_source) if at_source else None
        target_acct = asset_to_account.get(at_target) if at_target else None

        conn.execute(sa.text("""
            INSERT INTO recurring_schedules
                (id, user_id, type, name, amount, currency, schedule_day,
                 start_date, source_account_id, target_account_id,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, 'transfer', :name, :amount, 'KRW', :day,
                 :start_date, :source_account_id, :target_account_id,
                 :is_active, :created_at, :created_at)
        """), {
            "id": at_id,
            "user_id": at_user_id,
            "name": at_name,
            "amount": at_amount,
            "day": at_day,
            "start_date": at_created,
            "source_account_id": source_acct,
            "target_account_id": target_acct,
            "is_active": at_active,
            "created_at": at_created,
        })

    # ---------------------------------------------------------------
    # Step 12: Initial balance adjustments
    # ---------------------------------------------------------------
    # For each account, compare SUM(entries.amount) with old asset.principal.
    # If different, insert an adjustment entry.
    for old_asset_id, new_account_id in asset_to_account.items():
        old_row = old_asset_by_id.get(old_asset_id)
        if not old_row:
            continue

        old_principal = float(old_row[7] or 0)  # principal column
        if old_principal == 0:
            continue

        # Sum of all entries for this account
        result = conn.execute(sa.text("""
            SELECT COALESCE(SUM(amount), 0) FROM entries WHERE account_id = :acct_id
        """), {"acct_id": new_account_id}).scalar()
        current_sum = float(result or 0)

        diff = old_principal - current_sum
        if abs(diff) < 0.01:
            continue

        conn.execute(sa.text("""
            INSERT INTO entries (id, user_id, account_id, type,
                                amount, currency, memo, transacted_at, created_at)
            VALUES (:id, :user_id, :account_id, 'adjustment',
                    :amount, 'KRW', :memo, :transacted_at, :created_at)
        """), {
            "id": _uuid(),
            "user_id": user_id,
            "account_id": new_account_id,
            "amount": diff,
            "memo": "스키마 v2 마이그레이션 잔액 보정",
            "transacted_at": _now(),
            "created_at": _now(),
        })

    # ---------------------------------------------------------------
    # Step 13: Handle 한투 원화 principal -> ISA adjustment
    # ---------------------------------------------------------------
    if hantu_won_id and isa_id:
        hantu_won_row = old_asset_by_id.get(hantu_won_id)
        if hantu_won_row:
            hantu_principal = float(hantu_won_row[7] or 0)
            if hantu_principal != 0:
                # Check if ISA already got adjusted - add remaining 한투 원화 principal
                isa_sum = conn.execute(sa.text("""
                    SELECT COALESCE(SUM(amount), 0) FROM entries WHERE account_id = :acct_id
                """), {"acct_id": isa_id}).scalar()
                isa_sum = float(isa_sum or 0)

                # The ISA should have its own principal + 한투 원화 principal
                isa_row = old_asset_by_id.get(isa_id)
                isa_principal = float(isa_row[7] or 0) if isa_row else 0
                expected_total = isa_principal + hantu_principal
                diff = expected_total - isa_sum

                if abs(diff) >= 0.01:
                    conn.execute(sa.text("""
                        INSERT INTO entries (id, user_id, account_id, type,
                                            amount, currency, memo, transacted_at, created_at)
                        VALUES (:id, :user_id, :account_id, 'adjustment',
                                :amount, 'KRW', :memo, :transacted_at, :created_at)
                    """), {
                        "id": _uuid(),
                        "user_id": user_id,
                        "account_id": isa_id,
                        "amount": diff,
                        "memo": "한투 원화 → ISA 합병 잔액 보정",
                        "transacted_at": _now(),
                        "created_at": _now(),
                    })


# ===================================================================
# DROP OLD TABLES
# ===================================================================

def _drop_old_tables():
    """Drop old tables in reverse FK dependency order."""
    # First drop FKs from users table that reference assets
    op.drop_constraint("users_ibfk_1", "users", type_="foreignkey")
    op.drop_column("users", "salary_asset_id")

    # Drop tables in reverse dependency order
    op.drop_table("auto_transfers")
    op.drop_table("installments")
    op.drop_table("fixed_expenses")
    op.drop_table("recurring_incomes")
    op.drop_table("incomes")
    op.drop_table("budget_carryover_logs")
    op.drop_table("budget_carryover_settings")
    op.drop_table("expenses")
    op.drop_table("transactions")
    op.drop_table("news_clusters")
    op.drop_table("news_articles")
    op.drop_table("budget_categories")
    op.drop_table("assets")


# ===================================================================
# DOWNGRADE (not supported - restore from backup)
# ===================================================================

def downgrade() -> None:
    # Downgrade is not supported for this migration.
    # The data transformation is complex and lossy in reverse.
    # To roll back, restore from a database backup taken before upgrade.
    raise NotImplementedError(
        "Downgrade not supported for schema v2 migration. "
        "Please restore from a database backup."
    )
