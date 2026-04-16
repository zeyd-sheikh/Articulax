USE articulax;

ALTER TABLE session_artifacts
ADD COLUMN raw_metrics_json LONGTEXT NULL;

ALTER TABLE com_session_feedback
ADD COLUMN clarity_feedback TEXT NULL,
ADD COLUMN confidence_feedback TEXT NULL,
ADD COLUMN structure_feedback TEXT NULL,
ADD COLUMN relevance_feedback TEXT NULL,
ADD COLUMN vocabulary_feedback TEXT NULL;
