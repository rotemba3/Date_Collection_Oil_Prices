# Date Collection Oil Prices

This project collects oil-price related data, combines it with Twitter/X posts, stores the data in MongoDB, trains a prediction model, and exposes graph/prediction data through a Django API with a React frontend.

## Project Structure

```text
.
├── Requirements.txt
└── Data_Collection_Oil/
    ├── Selenium_data_pulls.py
    ├── app-back/
    │   ├── backend/              # Django project settings and root URLs
    │   ├── graphs/               # Django API views and routes
    │   ├── OilDatafiles/         # Data files, scraper, model training, prediction scripts
    │   ├── manage.py
    │   └── db.sqlite3
    └── my-app/                   # React frontend
```

## Main Components

- **Django backend**: serves API endpoints under `/api/`.
- **React frontend**: displays pages, graphs, prediction data, and database information.
- **Scraper scripts**: use Selenium to collect Twitter/X posts and oil price data.
- **Data processing scripts**: combine tweet data, oil prices, and gas/oil features.
- **Machine learning scripts**: train and run an oil-price prediction model.
- **MongoDB Atlas**: stores combined training data and prediction history.

## Python Setup

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r Requirements.txt
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r Requirements.txt
```

## Backend Setup

Go to the Django backend folder:

```bash
cd Data_Collection_Oil/app-back
python manage.py migrate
python manage.py runserver
```

The backend should run at:

```text
http://127.0.0.1:8000/
```

## API Endpoints

The backend exposes these routes:

```text
GET /api/graph/common-words/
GET /api/graph/tweets-vs-oil/
GET /api/graph/tweets-vs-oil-by-publisher/
GET /api/prediction/
GET /api/prediction/accuracy/
GET /api/get-all-data/
```

## Frontend Setup

Go to the React app folder:

```bash
cd Data_Collection_Oil/my-app
npm install
npm start
```

The frontend should run at:

```text
http://localhost:3000/
```

Frontend dependencies are managed by:

```text
Data_Collection_Oil/my-app/package.json
```

## Scraper Workflow

The scraper code is located in:

```text
Data_Collection_Oil/app-back/OilDatafiles/Scraper/
```

To run the main scraper:

```bash
cd Data_Collection_Oil/app-back/OilDatafiles/Scraper
python main.py
```

The scraper uses Selenium and expects a Chrome browser session with remote debugging enabled. On macOS, start Chrome like this:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-selenium-profile"
```

Then log in to X/Twitter in that Chrome window and leave it open while the scraper runs.

## Data and Model Scripts

Useful scripts under `Data_Collection_Oil/app-back/OilDatafiles/`:

```text
combine_data.py       # Combines scraped tweets with oil price data
sendtomongo.py        # Uploads combined data to MongoDB
Trainmodel.py         # Trains the prediction model
Scraper/main.py       # Runs the scraper workflow
Scraper/backfill.py   # Backfill-related scraper workflow
Scraper/predict_tomorrow.py
```

Some scripts currently contain hard-coded absolute local paths. Before running them on a new machine, update the path constants such as `BASE_DIR`, `DOWNLOADS_FOLDER`, and CSV file paths.

## MongoDB Configuration

The backend and data scripts connect to MongoDB Atlas using `pymongo`. Several files currently define the MongoDB connection string directly in code. For safer development, move the URI into an environment variable such as:

```bash
export MONGO_URI="your-mongodb-uri"
```

Then update the Python files to read from `os.environ["MONGO_URI"]`.

## Generated Files

The project includes generated/runtime files such as:

```text
db.sqlite3
*.pkl
*.csv
node_modules/
venv/
.venv/
__pycache__/
```

Avoid committing local virtual environments, installed frontend packages, Python cache files, or private credentials.

## Notes

- Use `Requirements.txt` for Python dependencies.
- Use `npm install` inside `Data_Collection_Oil/my-app` for frontend dependencies.
- Google Chrome must be installed for Selenium scraping.
- The scraper may need manual login to X/Twitter before it can collect tweets.
- If Excel files fail to load with pandas, confirm `openpyxl` is installed.
