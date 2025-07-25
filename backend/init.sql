-- GPUDex PostgreSQL Initialization Script
-- This script sets up the database schema and initial configuration

-- Create database if not exists (handled by POSTGRES_DB env var)
-- CREATE DATABASE IF NOT EXISTS gpudex_db;

-- Switch to our database (already connected via POSTGRES_DB)
-- \c gpudex_db;

-- Create extension for UUID generation if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant all privileges to our user
GRANT ALL PRIVILEGES ON DATABASE gpudex_db TO gpudex;

-- Create any additional indexes for performance
-- These will be created automatically by SQLAlchemy, but we can add custom ones here

-- Index for faster price history queries
-- CREATE INDEX IF NOT EXISTS idx_price_history_gpu_timestamp ON price_history(gpu_type, timestamp);
-- CREATE INDEX IF NOT EXISTS idx_price_history_provider ON price_history(provider);

-- Index for faster alert queries  
-- CREATE INDEX IF NOT EXISTS idx_alerts_email ON alerts(email);
-- CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
-- CREATE INDEX IF NOT EXISTS idx_alerts_gpu_type ON alerts(gpu_type);

-- Create a table for API keys (for future rate limiting)
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    user_email VARCHAR(255),
    requests_per_hour INTEGER DEFAULT 100,
    requests_per_day INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

-- Create index for API key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Insert a default API key for testing
INSERT INTO api_keys (key_name, api_key, user_email, requests_per_hour, requests_per_day) 
VALUES ('default', 'gpudex_demo_key_12345', 'demo@gpudex.com', 1000, 10000)
ON CONFLICT (api_key) DO NOTHING;

-- Create a table for usage analytics
CREATE TABLE IF NOT EXISTS usage_analytics (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    api_key VARCHAR(255),
    user_agent TEXT,
    ip_address INET,
    response_time_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for analytics
CREATE INDEX IF NOT EXISTS idx_analytics_endpoint ON usage_analytics(endpoint);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON usage_analytics(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_api_key ON usage_analytics(api_key);

-- Create a table for provider statistics
CREATE TABLE IF NOT EXISTS provider_stats (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(255) NOT NULL,
    gpu_type VARCHAR(100) NOT NULL,
    avg_price DECIMAL(10,4),
    min_price DECIMAL(10,4),
    max_price DECIMAL(10,4),
    availability_percentage DECIMAL(5,2),
    response_time_ms INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, gpu_type)
);

-- Create indexes for provider stats
CREATE INDEX IF NOT EXISTS idx_provider_stats_provider ON provider_stats(provider);
CREATE INDEX IF NOT EXISTS idx_provider_stats_gpu_type ON provider_stats(gpu_type);

-- Create a view for latest prices (useful for queries)
-- This will be populated by our application
-- CREATE OR REPLACE VIEW latest_prices AS
-- SELECT DISTINCT ON (provider, gpu_type) 
--     provider, gpu_type, price, availability, timestamp
-- FROM price_history 
-- ORDER BY provider, gpu_type, timestamp DESC;

-- Set up some initial configuration
CREATE TABLE IF NOT EXISTS app_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT INTO app_config (key, value, description) VALUES 
('max_alerts_per_user', '10', 'Maximum number of alerts per email address'),
('alert_check_interval_minutes', '5', 'How often to check alerts in minutes'),
('default_rate_limit_per_hour', '100', 'Default API rate limit per hour'),
('email_enabled', 'true', 'Whether email notifications are enabled'),
('arbitrage_threshold_percentage', '10', 'Minimum percentage difference for arbitrage alerts')
ON CONFLICT (key) DO NOTHING;

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to app_config table
CREATE TRIGGER update_app_config_updated_at 
    BEFORE UPDATE ON app_config 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Display initialization completion
SELECT 'GPUDex PostgreSQL database initialized successfully!' as status; 