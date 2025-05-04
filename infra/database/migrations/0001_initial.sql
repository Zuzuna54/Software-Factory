-- Initial migration script
-- Migration: 0001_initial
-- Created: 2023-09-01

BEGIN;

-- Include the full schema.sql content
\i 'infra/database/schema.sql'

COMMIT; 