-- users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- api_credentials table
CREATE TYPE service_provider_enum AS ENUM ('IBM', 'OTHER');

CREATE TABLE IF NOT EXISTS api_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_provider service_provider_enum NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, service_provider)
);

-- job_logs table
CREATE TYPE job_type_enum AS ENUM ('ENTROPY', 'SIMULATION', 'ML_ORACLE');
CREATE TYPE job_status_enum AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED');

CREATE TABLE IF NOT EXISTS job_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_type job_type_enum NOT NULL,
    status job_status_enum NOT NULL DEFAULT 'PENDING',
    execution_time_ms INTEGER,
    hardware_backend_used VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- update trigger for updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_job_logs_modtime
    BEFORE UPDATE ON job_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Insert a default user for testing
INSERT INTO users (username) VALUES ('testuser') ON CONFLICT (username) DO NOTHING;
