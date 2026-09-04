# Tedile

Tedile is a local service provider marketplace that connects customers with
independent professionals such as plumbers, electricians, carpenters, and
painters.

## Key Features

- Service browsing by category and location
- Location-based provider search with map integration
- Provider profiles, verification, ratings, and reviews
- Direct WhatsApp and phone contact
- Customer and provider dashboards
- Admin dashboard

## Project Structure

```
Tedile/
├── app/             # Flask application package
├── static/          # JavaScript and CSS assets
├── templates/       # Server-rendered HTML templates
├── tests/           # Application tests
├── database/        # Database setup and seed scripts
├── migrations/      # Alembic migrations
├── app.py           # Local application entry point
├── config.py        # Application configuration
├── requirements.txt # Python dependencies
└── render.yaml      # Render deployment configuration
```

## Local Development

From the repository root:

```bash
cd Tedile
source ../.venv/bin/activate
pip install -r requirements.txt
python app.py
```

The application is available at `http://127.0.0.1:5000`.

Configure the local database and other secrets in `.env` as needed. The local
PostgreSQL database is named `tedile_dev`:

```bash
DATABASE_URL=postgresql://user:password@localhost/tedile_dev
```

Database setup and seed scripts are available in `database/`. Schema changes
are managed through the migrations in `migrations/`.

## Render Deployment

The included `Tedile/render.yaml` defines the `tedile` web service. Render
installs the dependencies and starts the Flask application with Gunicorn. The
Flask application serves the web interface and API from the same service.

To deploy, create a Render Blueprint connected to this repository and use the
included `render.yaml`. Configure the required secret and database environment
variables in Render before starting the service.

## Tech Stack

**Backend:** Flask, SQLAlchemy, PostgreSQL, and PostGIS

**Frontend:** Server-rendered HTML, JavaScript, and CSS

**Maps:** Map integration through the application’s configured map services

**Deployment:** Gunicorn on Render

## Contributing

1. Create a feature branch.
2. Run the test suite with `pytest` from the `Tedile/` directory.
3. Commit your changes and open a pull request.

## License

This project is licensed under the MIT License.

**Status:** In Development

**Version:** 0.1.0
