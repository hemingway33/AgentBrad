# CLAUDE.md — AgentBrad Codebase Guide

## Project Overview

**AgentBrad** is an AI-powered personal financial intelligence agent built with **Django**. It helps users manage debt, track budgets, set financial goals, and receive AI-driven advice. The project is structured as a Django multi-app monorepo.

The project was bootstrapped with `django-admin startproject finance_manager` and expanded with five Django apps:

```
finance_manager/   # Django project root (settings, root URL conf, celery)
bookkeeping/       # Double-entry bookkeeping, accounts, transactions, financial statements
debt_manager/      # Debt accounts, income tracking, payment plans
budget_tracker/    # Budget categories and expense tracking
goals/             # Financial goals (savings, debt payoff, investments)
debt_advisor/      # AI chat advisor, gamification, achievements, reminders
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Required Environment Variables

Set these before running in production (defaults are provided for local development):

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | insecure dev key |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DB_ENGINE` | Database engine | `django.db.backends.sqlite3` |
| `DB_NAME` | Database name | `db.sqlite3` |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 advisor | empty |
| `QUICKBOOKS_CLIENT_ID` | QuickBooks OAuth2 client ID | empty |
| `QUICKBOOKS_CLIENT_SECRET` | QuickBooks OAuth2 client secret | empty |
| `QUICKBOOKS_REDIRECT_URI` | QuickBooks OAuth2 redirect URI | empty |
| `QUICKBOOKS_ENVIRONMENT` | `sandbox` or `production` | `sandbox` |
| `DEFAULT_FROM_EMAIL` | Email sender for reminders | `noreply@agentbrad.com` |
| `EMAIL_BACKEND` | Django email backend | console backend |
| `CELERY_BROKER_URL` | Celery broker | `redis://localhost:6379/0` |

---

## Directory Structure

```
AgentBrad/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── templates/
│   └── base.html             # Base HTML template (Bootstrap 5)
├── finance_manager/          # Django project config
│   ├── __init__.py           # Celery app auto-discovery
│   ├── settings.py           # Full Django settings (env-based secrets)
│   ├── urls.py               # Root URL routing (admin, web UI, API)
│   ├── wsgi.py               # WSGI application
│   ├── asgi.py               # ASGI application
│   └── celery.py             # Celery configuration
├── bookkeeping/              # Core double-entry bookkeeping app
│   ├── __init__.py
│   ├── apps.py               # BookkeepingConfig
│   ├── admin.py              # Django admin registration
│   ├── models.py             # Account, Transaction, TransactionLine, QuickBooksIntegration, FinancialStatement
│   ├── views.py              # DashboardView, TransactionListView, TransactionCreateView, FinancialReportView, MetricsView, IntegrationsView
│   ├── forms.py              # TransactionForm, TransactionLineInlineFormSet
│   ├── utils.py              # calculate_account_balance(), generate_trial_balance()
│   ├── metrics.py            # BusinessMetrics class (financial ratios)
│   ├── services.py           # QuickBooksService (sync accounts/transactions via OAuth)
│   ├── urls.py               # Web UI routes (app_name='bookkeeping')
│   ├── templates/bookkeeping/
│   │   ├── dashboard.html
│   │   ├── transaction_list.html
│   │   ├── transaction_form.html
│   │   ├── financial_reports.html
│   │   ├── metrics.html
│   │   └── integrations.html
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py           # CustomAuthToken (login), LogoutView
│   │   ├── serializers.py    # AccountSerializer, TransactionSerializer, MetricsSerializer
│   │   ├── views.py          # AccountViewSet, TransactionViewSet, MetricsAPIView, DashboardAPIView
│   │   └── urls.py           # DRF router + metric/dashboard endpoints
│   └── integrations/
│       ├── __init__.py
│       ├── base.py           # AccountingSoftwareIntegration ABC
│       ├── xero_integration.py  # XeroIntegration
│       └── sage_integration.py  # SageIntegration
├── debt_manager/
│   ├── __init__.py
│   ├── apps.py               # DebtManagerConfig
│   ├── admin.py              # Django admin registration
│   └── models.py             # DebtAccount, Income, DebtPaymentPlan
├── budget_tracker/
│   ├── __init__.py
│   ├── apps.py               # BudgetTrackerConfig
│   ├── admin.py              # Django admin registration
│   └── models.py             # Category, Expense
├── goals/
│   ├── __init__.py
│   ├── apps.py               # GoalsConfig
│   ├── admin.py              # Django admin registration
│   └── models.py             # FinancialGoal
├── debt_advisor/             # AI advisor + gamification engine
│   ├── __init__.py
│   ├── apps.py               # DebtAdvisorConfig
│   ├── admin.py              # Django admin registration
│   ├── models.py             # ConversationSession, Message, FinancialAdvice, UserProgress,
│   │                         # Achievement, UserAchievement, Reminder, Reward, UserReward,
│   │                         # Level, Challenge, UserChallenge
│   ├── services.py           # DebtAdvisorService (OpenAI GPT-4 via v1.x client)
│   ├── tasks.py              # Celery task: process_daily_checks()
│   ├── urls.py               # API routes for conversation and gamification
│   ├── api/
│   │   ├── __init__.py
│   │   └── views.py          # ConversationViewSet, GamificationViewSet
│   ├── services/
│   │   ├── __init__.py
│   │   ├── achievement_service.py   # AchievementService (checks & awards achievements)
│   │   ├── gamification_service.py  # GamificationService (levels, rewards, challenges)
│   │   └── reminder_service.py      # ReminderService (payment & check-in reminders via email)
│   └── management/
│       ├── __init__.py
│       └── commands/
│           ├── __init__.py
│           └── process_reminders.py  # Management command: python manage.py process_reminders
├── terminal                  # Shell commands used to bootstrap the project (not executable)
├── README.md
└── LICENSE
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.1 |
| REST API | Django REST Framework (DRF) |
| Authentication | DRF Token Authentication + Session Authentication |
| UI Styling | Bootstrap 5 via `crispy_forms` + `crispy_bootstrap5` |
| AI Advisor | OpenAI GPT-4 (v1.x SDK: `openai.OpenAI().chat.completions.create`) |
| Async Tasks | Celery (`@shared_task`) with Redis broker |
| Bookkeeping Integrations | QuickBooks (`intuitlib`, `python-quickbooks`), Xero (`pyxero`), Sage One (`sage-one`) |
| Database | Django ORM — SQLite (default), configurable via env vars for PostgreSQL |

---

## Key Configuration (`finance_manager/settings.py`)

### Installed Apps
```
debt_manager, budget_tracker, goals, bookkeeping, debt_advisor
crispy_forms, crispy_bootstrap5
rest_framework, rest_framework.authtoken
```

### DRF Settings
- Authentication: `TokenAuthentication` (primary), `SessionAuthentication` (fallback)
- Permissions: `IsAuthenticated` by default
- Pagination: `PageNumberPagination`, page size = 20

### Celery
- Configured in `finance_manager/celery.py` with auto-discovery
- Initialized in `finance_manager/__init__.py`
- Broker: Redis (default `redis://localhost:6379/0`)

---

## Data Models

### `bookkeeping`
- **`Account`** — Chart of accounts. Types: `ASSET`, `LIABILITY`, `EQUITY`, `REVENUE`, `EXPENSE`.
- **`Transaction`** — Journal entry header. Status: `PENDING` -> `POSTED` -> `RECONCILED`. Source: `MANUAL`, `QUICKBOOKS`, `IMPORT`.
- **`TransactionLine`** — Double-entry journal line (debit/credit amounts against an Account). Enforced balance: total debits must equal total credits (via `TransactionLineFormSet.clean()`).
- **`QuickBooksIntegration`** — Per-user OAuth tokens for QuickBooks sync.
- **`FinancialStatement`** — Stored balance sheets, income statements, cash flow statements (JSON blob).

### `debt_manager`
- **`DebtAccount`** — A debt with balance, interest rate, minimum payment, due date. Types: credit card, student loan, mortgage, personal loan, other.
- **`Income`** — Income source with amount and frequency (weekly/biweekly/monthly/annual).
- **`DebtPaymentPlan`** — Links a DebtAccount to a payoff strategy (Avalanche or Snowball) with a target payment and estimated payoff date.

### `budget_tracker`
- **`Category`** — Budget category with a spending limit per user.
- **`Expense`** — An expense tied to a category, with an `is_essential` flag.

### `goals`
- **`FinancialGoal`** — Goal with target amount, current amount, deadline, and priority (1-5). Categories: debt payoff, emergency fund, savings, investment. Has `progress_percentage()` method.

### `debt_advisor`
- **`ConversationSession`** — Active AI chat session with JSON context (total debt, recent spending).
- **`Message`** — Individual chat message (user or bot). Types: `GENERAL`, `ADVICE`, `REMINDER`, `ENCOURAGEMENT`, `ALERT`.
- **`FinancialAdvice`** — Curated advice articles by category.
- **`UserProgress`** — Per-user engagement state: mood score (1-10), engagement level, points, achievements JSON.
- **`Achievement`** / **`UserAchievement`** — Achievement definitions and per-user earning records.
- **`Reminder`** — Scheduled notifications with repeat intervals (daily/weekly/monthly/custom).
- **`Reward`** / **`UserReward`** — Redeemable rewards (premium features, tools, consultations) with points cost and duration.
- **`Level`** — Gamification level with points threshold and perks.
- **`Challenge`** / **`UserChallenge`** — Timed challenges (savings, debt payment, budget streak, education) with JSON progress tracking.

---

## API Endpoints

### Authentication
| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/login/` | Obtain auth token (`CustomAuthToken`) — returns `{token, user}` |
| POST | `/api/auth/logout/` | Delete auth token |

### Bookkeeping API (prefix: `/api/`)
| Method | URL | Description |
|---|---|---|
| GET/POST | `/api/accounts/` | List/create accounts |
| GET/PUT/DELETE | `/api/accounts/{id}/` | Account detail |
| GET/POST | `/api/transactions/` | List/create transactions (nested lines) |
| GET | `/api/transactions/recent/` | Last 5 transactions |
| GET | `/api/metrics/` | All `BusinessMetrics` ratios |
| GET | `/api/dashboard/` | Accounts + recent transactions + metrics combined |

### Debt Advisor API (prefix: `/api/`)
| Method | URL | Description |
|---|---|---|
| POST | `/api/conversation/` | Send message, get GPT-4 response |
| GET | `/api/conversation/history/` | Last 50 messages |
| GET | `/api/gamification/` | Level, points, available rewards, active challenges |
| POST | `/api/gamification/redeem_reward/` | Redeem reward by `reward_id` |
| POST | `/api/gamification/join_challenge/` | Join challenge by `challenge_id` |
| POST | `/api/gamification/{id}/update_progress/` | Update challenge progress |

### Web UI URLs (`bookkeeping` app)
| URL | View | Name |
|---|---|---|
| `/` | `DashboardView` | `bookkeeping:dashboard` |
| `/transactions/` | `TransactionListView` | `bookkeeping:transaction-list` |
| `/transactions/create/` | `TransactionCreateView` | `bookkeeping:transaction-create` |
| `/reports/` | `FinancialReportView` | `bookkeeping:financial-reports` |
| `/metrics/` | `MetricsView` | `bookkeeping:metrics` |
| `/integrations/` | `IntegrationsView` | `bookkeeping:integrations` |

### Admin
| URL | Description |
|---|---|
| `/admin/` | Django admin (all models registered) |

---

## Core Business Logic

### Double-Entry Bookkeeping
- Every `Transaction` has one or more `TransactionLine` records.
- `TransactionLineFormSet` validates that **sum of debits == sum of credits** before saving.
- Account balances are calculated dynamically via ORM annotation:
  `balance = Sum(debit_amount) - Sum(credit_amount)`
- `ASSET` and `EXPENSE` accounts have a debit-normal balance; `LIABILITY`, `EQUITY`, `REVENUE` have a credit-normal balance (handled in `utils.calculate_account_balance()`).

### Financial Metrics (`bookkeeping/metrics.py`)
`BusinessMetrics` class computes ratios on demand:
- **Quick Ratio** — (Current Assets - Inventory) / Current Liabilities
- **Current Ratio** — Current Assets / Current Liabilities
- **Operating Cash Flow Ratio** — Operating Cash Flow / Current Liabilities
- **Gross Profit Margin** — (Revenue - COGS) / Revenue x 100
- **Debt-to-Equity Ratio** — Total Liabilities / Total Equity
- **Accounts Receivable Turnover** — Net Credit Sales / Avg Accounts Receivable

All methods return `None` if the denominator is zero. Account filtering uses name-based keyword matching (e.g., accounts with "receivable" in the name for A/R calculations).

### AI Advisor (`debt_advisor/services.py`)
- `DebtAdvisorService` maintains a `ConversationSession` per user.
- On initialization, it builds a context dict with `total_debt`, `num_debts`, `recent_spending`.
- Uses OpenAI v1.x client: `openai.OpenAI(api_key=...).chat.completions.create()` with model `gpt-4`, temperature `0.7`, max 150 tokens.
- Stores both user and bot messages in the `Message` model.
- Classifies responses into message types via keyword matching (REMINDER, ENCOURAGEMENT, ADVICE, GENERAL).

### Gamification Engine
- **Points** = achievement points + completed challenge rewards. Tracked on `UserProgress.points`.
- **Levels** are defined in the `Level` model with `points_required` thresholds.
- **`AchievementService`** checks debt reduction milestones ($1k, $5k, debt-free), savings milestones ($1k, $5k), budget creation, and engagement (session count). Gracefully handles missing achievement definitions.
- **`GamificationService`** handles reward redemption, challenge enrollment, and challenge progress tracking.
- **`ReminderService`** creates payment reminders (3 days before due date) and weekly check-in reminders; sends via Django `send_mail`. Creates in-app notifications via `Message` model when an active session exists.

### Third-Party Integrations
All integrations extend `AccountingSoftwareIntegration` (ABC with `authenticate`, `sync_accounts`, `sync_transactions`, `sync_contacts`):
- **QuickBooks** (`QuickBooksService`) — Full OAuth2 via `intuitlib`; syncs accounts with `update_or_create`.
- **Xero** (`XeroIntegration`) — OAuth2 via `pyxero`.
- **Sage One** (`SageIntegration`) — API key auth via `sage-one` library.

---

## Development Conventions

### User Data Scoping
Every model that holds user data has a `user = ForeignKey(User, on_delete=CASCADE)`. All querysets **must** filter by `user=request.user`. Views and ViewSets enforce this in `get_queryset()` and `perform_create()`.

### Class-Based Views
- Web UI views use Django's generic CBVs (`TemplateView`, `ListView`, `CreateView`) with `LoginRequiredMixin`.
- API views use DRF `ModelViewSet` or `APIView`/`ViewSet` depending on complexity.

### Serializers
- Nested writes (e.g., `Transaction` with `TransactionLine` list) are handled by overriding `create()` in the serializer to pop nested data and create child objects.
- Annotated fields (e.g., `balance` on `Account`) are declared as `read_only=True` in the serializer.

### URL Namespacing
- The `bookkeeping` web UI uses `app_name = 'bookkeeping'` — always reference these URLs as `bookkeeping:dashboard`, etc.
- API URLs are registered via DRF `DefaultRouter`.

### Forms
- Use `crispy_forms` with Bootstrap 5 (`CRISPY_TEMPLATE_PACK = "bootstrap5"`).
- Transaction lines use `inlineformset_factory` with custom validation in `TransactionLineFormSet`.

### Templates
- Base template at `templates/base.html` provides Bootstrap 5 navbar, message alerts, and block structure.
- App templates at `bookkeeping/templates/bookkeeping/` extend `base.html`.

---

## Background Tasks

### Celery
`debt_advisor/tasks.py` defines `process_daily_checks()` as a `@shared_task`. It iterates all active users and:
1. Calls `ReminderService.send_due_reminders()` for each.
2. Calls `AchievementService.check_achievements()` for each.

### Management Command
```bash
python manage.py process_reminders
```
Manually triggers reminder dispatch for all active users (same logic as the Celery task but synchronous).

---

## Remaining Work

1. **No migrations** — Run `python manage.py makemigrations` and `python manage.py migrate` before first use.
2. **No tests** — Test files need to be created for all apps.
3. **Xero integration incomplete** — `XeroIntegration` uses an `external_id` field not on the `Account` model, and `_map_account_type()` is not implemented.
4. **Sage integration stub** — `SageIntegration.sync_accounts()` has only a placeholder comment.
5. **QuickBooks transaction sync** — `QuickBooksService.sync_transactions()` is a stub (`pass`).
6. **No `.env` file** — A `.env` example or template would help with onboarding.
