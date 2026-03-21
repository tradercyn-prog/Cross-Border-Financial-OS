# Cross-Border Financial OS

A local-first, privacy-focused desktop application engineered for digital nomads and expats to manage multi-currency cash flow, track cross-border assets, and simulate real-time runway across different global economies.

## 🚀 The Problem
Managing finances as an expat is notoriously complex. Earning in USD but spending in PHP, JPY, or EUR creates a constantly shifting baseline. Traditional spreadsheets rely on fragile, delayed web-scraping for FX rates, and standard budgeting apps do not understand the concept of holding assets in multiple fiat currencies simultaneously. 

## 💡 The Solution
Cross-Border Financial OS replaces fragile cloud spreadsheets with a compiled, strictly-typed Python desktop engine. It integrates directly with the Wise API to fetch live mid-market exchange rates, normalizes local expenses into a unified home currency using the Polars data engine, and calculates strict weekly pacing targets to ensure financial survival.

## 🛠️ Tech Stack
* **Frontend:** PySide6 (Qt for Python) - Modern, dark-mode desktop UI.
* **Backend:** Python 3.12+
* **Data Processing:** Polars - High-performance DataFrame library for lightning-fast burn rate calculations.
* **Database:** SQLAlchemy & SQLite - Local-first data storage. No cloud leaks.
* **Integrations:** Wise (TransferWise) API - Live FX rates and automated balance syncing.
* **Data Visualization:** Matplotlib - Dynamic runway and pacing charts.

## ⚙️ Core Features
* **Live FX Telemetry:** Automatically pulls real-time exchange rates to calculate global net worth.
* **Strict Weekly Pacing:** An aggressive envelope-math system that compares your liquid cash against the current day of the month, telling you exactly how much you are "Safe to Spend" right now.
* **The "Next Stop" Scenario Engine:** Enter a target country and an estimated local monthly cost. The engine pulls the live exchange rate and calculates exactly how many months your current liquid cash will survive in that specific economy.
* **Cross-Border Asset Tracking:** Seamlessly tracks multi-currency bank accounts, brokerages, and e-wallets.
* **CRUD Bills Planner:** Dynamic logging and adjustment of fixed obligations and weekly lifestyle costs, with built-in time horizon normalizers (Weekly, Bi-Weekly, Monthly, etc.).

## 🔐 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone [https://github.com/yourusername/cross-border-financial-os.git](https://github.com/yourusername/cross-border-financial-os.git)
   cd cross-border-financial-os

2. Create a Virtual Environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt

4. Environment Variables
This application requires a Wise API token to function at full capacity. Create a .env file in the root directory and add your token:
WISE_API_TOKEN=your_wise_api_key_here

5. Launch the OS
python main.py


🏗️ Architecture Notes
The application is built on a modular architecture separating the UI (PySide6 Tabs), the Core Logic (Calculations & State Management), 
and External Integrations (Wise API). The database schema is built dynamically on the first boot using SQLAlchemy ORM.
