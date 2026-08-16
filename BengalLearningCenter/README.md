# Bengal Learning Center

A modern school management application focused on:

- Staff attendance tracking
- Student attendance monitoring
- Notice publication and announcement board
- School billing and fee management
- Fee payment tracking and collection dashboard

## Features

- Dashboard overview for school operations
- Staff attendance records with present/absent summary
- Student attendance by class and section
- Notice board for principal, admin, and class announcements
- Billing sheet for monthly fees, transport, and other charges
- Fee payment status tracking with pending and paid summaries
- Simple API backend ready for future database integration

## Tech Stack

- Python 3.11+
- Flask
- HTML, CSS, JavaScript

## Project Structure

```text
BengalLearningCenter/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── app.js
│   └── styles.css
├── templates/
│   └── index.html
└── __pycache__/
```

## Run locally

```bash
cd BengalLearningCenter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

- http://127.0.0.1:5000

## Notes

This is an initial working school management starter app. It uses sample data so the UI and workflows can be reviewed quickly before connecting to a real database or authentication system.

## Production architecture

For a real deployment, keep file storage separate from relational data:

- PostgreSQL stores structured information such as student records, attendance, fees, and file metadata.
- S3 stores the actual uploaded files such as student photos, receipts, notices, and PDFs.

Example:

```text
Student row:
  id = 125
  name = "Ayesha Rahman"
  photo_url = "https://bengal-learning-center.s3.ap-south-1.amazonaws.com/students/125/profile.jpg"
```

This pattern means:

- PostgreSQL = structured data
- S3 = uploaded files

Recommended Render deployment configuration:

```env
SECRET_KEY=your-long-random-secret
FLASK_DEBUG=false
DATABASE_URL=postgresql://user:password@host:5432/bengal_learning_center
AWS_REGION=ap-south-1
S3_BUCKET_NAME=bengal-learning-center
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

Render can provision a PostgreSQL database and attach it as an environment variable automatically. The app then uses the `DATABASE_URL` for schema and metadata storage while S3 handles uploaded files.

Recommended folders for S3:

```text
students/
receipts/
notices/
documents/
backups/
```

The app should never store large uploaded files directly in the Flask server folder. Instead, the server should upload the file to S3 and save only the file reference or URL in the database.
