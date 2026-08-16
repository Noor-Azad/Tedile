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
