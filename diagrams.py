gantt
    title Project Timeline (Indicative 12 Weeks)
    dateFormat  YYYY-MM-DD
    section Planning
    Requirements & Scope           :done, a1, 2026-01-06, 10d
    Architecture & Design          :done, a2, after a1, 7d
    section Core Development
    Backend Auth + DB              :done, b1, after a2, 12d
    Frontend Role Dashboards       :done, b2, after b1, 14d
    section ML Pipeline
    Data Ingestion + Preprocess    :done, c1, after b1, 10d
    Training + Experiments         :done, c2, after c1, 12d
    Deploy + Prediction APIs       :done, c3, after c2, 8d
    section Intelligence Features
    Sentiment + News Integration   :done, d1, after c3, 8d
    Alerts + Email Scheduler       :active, d2, after d1, 8d
    Portfolio + Backtesting        :done, d3, after c3, 10d
    section Validation
    Testing + Hardening            :e1, after d2, 10d
    Report Finalization            :e2, after e1, 7d

flowchart LR
    U[User Dashboard] -->|HTTPS| API[FastAPI Backend]
    R[Researcher Workbench] -->|HTTPS| API
    A[Admin Dashboard] -->|HTTPS| API

    API --> DB[(SQLite: users, sessions, alerts, experiments, prices)]
    API --> ART[(Model Artifacts: joblib)]
    API --> YF[Yahoo Finance]
    API --> CG[CoinGecko]
    API --> GN[Google News RSS]
    API --> XAPI[X API / Nitter RSS]
    API --> EM[EmailJS]
    API --> LLM[Gemini API]

    API --> WRK[Hourly Alert Worker]
    WRK --> DB
    WRK --> EM

flowchart TB
    User((User)) --> UC1[Request Prediction]
    User --> UC2[Manage Alerts]
    User --> UC3[View Portfolio & Backtest]
    User --> UC4[Read Sentiment/News]
    User --> UC5[Enable 2FA]

    Researcher((Researcher)) --> RC1[Fetch Data]
    Researcher --> RC2[Preprocess Data]
    Researcher --> RC3[Train Models]
    Researcher --> RC4[Deploy Experiment]
    Researcher --> RC5[Compare Experiments]

    Admin((Admin)) --> AC1[Approve Users]
    Admin --> AC2[Manage Roles]
    Admin --> AC3[Configure Assets/Models]
    Admin --> AC4[View Logs & API Usage]

flowchart TD
    S[Hourly Scheduler Tick] --> Q[Load enabled alerts + approved users]
    Q --> C[For each symbol: fetch latest price/change]
    C --> T{Alert Type}
    T -->|target| E1[Evaluate threshold crossing]
    T -->|percent| E2[Evaluate 24h change]
    T -->|sentiment| E3[Fetch sentiment + compare label]
    E1 --> R{Triggered?}
    E2 --> R
    E3 --> R
    R -->|No| N[Skip]
    R -->|Yes| CD{Cooldown elapsed?}
    CD -->|No| N
    CD -->|Yes| M[Send EmailJS notification]
    M --> U[Update last_notified_at]

erDiagram
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ ACTIVITY_LOGS : generates
    USERS ||--o{ PREDICTION_HISTORY : creates
    USERS ||--o{ ALERTS : owns
    USERS ||--o{ PORTFOLIO_HOLDINGS : owns
    USERS ||--o{ EXPERIMENTS : runs

    CRYPTO_CONFIGS ||--o{ HISTORICAL_PRICES : defines_symbol
    CRYPTO_CONFIGS ||--o{ EXPERIMENTS : modeling_target
    CRYPTO_CONFIGS ||--o{ ALERTS : alert_target
    CRYPTO_CONFIGS ||--o{ PORTFOLIO_HOLDINGS : holding_symbol

    MODEL_CONFIGS ||--o{ EXPERIMENTS : constrains_options

    USERS {
      int id PK
      string email
      string role
      string status
      string twofa_secret
      bool twofa_enabled
      datetime created_at
    }

    EXPERIMENTS {
      int id PK
      int researcher_id FK
      string symbol
      string model_name
      string metrics_json
      string artifact_path
      bool is_deployed
      datetime created_at
    }

    ALERTS {
      int id PK
      int user_id FK
      string symbol
      string alert_type
      float threshold_value
      string direction
      string sentiment_label
      bool is_enabled
      bool email_enabled
      datetime last_notified_at
    }

flowchart LR
    C[Code Commit] --> L[Lint + Format Check]
    L --> T[Unit/API Tests]
    T --> S[SAST + Dependency Scan]
    S --> B[Build Artifacts]
    B --> D[Deploy to Staging]
    D --> U[UAT + DAST]
    U --> P[Promote to Production]
    P --> M[Post-Deploy Monitoring]