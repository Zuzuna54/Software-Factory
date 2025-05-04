-- Initialize database with schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Include the schema from the schema.sql file
\i '/app/infra/database/schema.sql' 