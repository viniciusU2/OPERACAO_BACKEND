ALTER TABLE usuarios
  ADD COLUMN auth_version INT NOT NULL DEFAULT 0;

CREATE TABLE password_reset_tokens (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_password_reset_token_hash (token_hash),
  KEY ix_password_reset_tokens_user_id (user_id),
  KEY ix_password_reset_tokens_expires_at (expires_at),
  KEY idx_password_reset_user_active (user_id, used_at, expires_at),
  CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
);
