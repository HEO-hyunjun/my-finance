# New v2 models
from app.models.account import Account, AccountType, InterestType  # noqa: F401
from app.models.security import Security, SecurityPrice, AssetClass, DataSource  # noqa: F401
from app.models.entry import Entry, EntryGroup, EntryType, GroupType  # noqa: F401
from app.models.category import Category, CategoryDirection  # noqa: F401
from app.models.recurring_schedule import RecurringSchedule, ScheduleType  # noqa: F401

# Keep existing models that are still used
from app.models.user import User  # noqa: F401
from app.models.portfolio import AssetSnapshot, PortfolioTarget, RebalancingAlert, GoalAsset, AccountSnapshot  # noqa: F401
from app.models.budget import BudgetCategory, Expense, FixedExpense, Installment, BudgetCarryoverSetting, BudgetCarryoverLog  # noqa: F401

# Old models kept for migration compatibility and Phase 2 services
from app.models.asset import Asset  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.income import Income, RecurringIncome  # noqa: F401
from app.models.auto_transfer import AutoTransfer  # noqa: F401
from app.models.insight import AIInsightRecord  # noqa: F401
from app.models.news import NewsArticleDB, NewsCluster  # noqa: F401
from app.models.settings import ApiKey, LlmSetting  # noqa: F401
from app.models.conversation import Conversation, Message  # noqa: F401
