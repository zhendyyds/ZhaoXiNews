CREATE TABLE IF NOT EXISTS ai_documents (
    id CHAR(32) PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    filename VARCHAR(255) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT uq_ai_document_owner_hash UNIQUE (user_id, sha256),
    CONSTRAINT fk_ai_document_user FOREIGN KEY (user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
