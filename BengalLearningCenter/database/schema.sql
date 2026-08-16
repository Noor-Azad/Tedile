CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    class_name VARCHAR(120),
    parent_name VARCHAR(255),
    parent_phone VARCHAR(40),
    attendance_score INTEGER DEFAULT 0,
    status VARCHAR(80) DEFAULT 'Good',
    photo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_uploads (
    id SERIAL PRIMARY KEY,
    owner_id VARCHAR(255) NOT NULL,
    category VARCHAR(120) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    file_url TEXT NOT NULL,
    mime_type VARCHAR(120) DEFAULT 'application/octet-stream',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id SERIAL PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(40) NOT NULL,
    arrival_time VARCHAR(40),
    departure_time VARCHAR(40),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fee_payments (
    id SERIAL PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(40) DEFAULT 'Due',
    payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
