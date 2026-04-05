CREATE DATABASE IF NOT EXISTS articulax;
USE articulax;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    account_password VARCHAR(500) NOT NULL,
    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resumes (
    resume_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    file_name VARCHAR(225) NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)
    REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mode VARCHAR(25) NOT NULL,
    score INT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    UNIQUE (session_id, mode),
    FOREIGN KEY (user_id)
    REFERENCES users(user_id),
    CHECK (score >= 0 AND score <= 100),
    CHECK (mode IN ('communication', 'interview', 'presentation'))
);

CREATE TABLE IF NOT EXISTS session_artifacts (
    artifact_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL UNIQUE,
    transcript_text TEXT NOT NULL,
    audio_file_path TEXT NOT NULL,
    FOREIGN KEY (session_id) 
    REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS com_sessions (
    session_id INT PRIMARY KEY,
    mode VARCHAR(25) NOT NULL DEFAULT 'communication',
    topic VARCHAR(50) NOT NULL,
    audience VARCHAR(20) NOT NULL,
    tone VARCHAR(20) NOT NULL,
    duration INT NOT NULL,
    FOREIGN KEY (session_id)
    REFERENCES sessions(session_id),
    CHECK (mode = 'communication'),
    CHECK (audience IN ('kids', 'general', 'professional')),
    CHECK (tone IN ('formal', 'persuasive', 'casual'))
);

CREATE TABLE IF NOT EXISTS com_session_scores (
    session_id INT PRIMARY KEY,
    clarity_score INT NOT NULL,
    confidence_score INT NOT NULL,
    structure_score INT NOT NULL,
    relevance_score INT NOT NULL,
    vocabulary_score INT NOT NULL,
    FOREIGN KEY (session_id) 
    REFERENCES com_sessions(session_id),
    CHECK (clarity_score >= 0 AND clarity_score <= 100),
    CHECK (confidence_score >= 0 AND confidence_score <= 100),
    CHECK (structure_score >= 0 AND structure_score <= 100),
    CHECK (relevance_score >= 0 AND relevance_score <= 100),
    CHECK (vocabulary_score >= 0 AND vocabulary_score <= 100)
);

CREATE TABLE IF NOT EXISTS com_session_feedback (
    session_id INT PRIMARY KEY,
    feedback TEXT,
    FOREIGN KEY (session_id) 
    REFERENCES com_sessions(session_id)
);
