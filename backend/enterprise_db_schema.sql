-- Enterprise API Management Database Schema
-- Enhanced tables for organizations, teams, API keys, and billing

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) NOT NULL DEFAULT 'free',
    billing_email VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    scopes JSONB DEFAULT '[]', -- Array of permission scopes
    invited_by VARCHAR(255),
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    joined_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(organization_id, email)
);

-- Enhanced API keys table
CREATE TABLE IF NOT EXISTS api_keys_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE, -- SHA256 hash of the actual key
    description TEXT,
    scopes JSONB DEFAULT '[]', -- Array of permission scopes
    created_by VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count BIGINT DEFAULT 0,
    
    -- Security features
    ip_whitelist JSONB, -- Array of allowed IP addresses/ranges
    rate_limit_override JSONB, -- Custom rate limits for this key
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- API usage logs for detailed analytics and billing
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys_v2(id) ON DELETE SET NULL,
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms FLOAT NOT NULL,
    request_size_bytes INTEGER DEFAULT 0,
    response_size_bytes INTEGER DEFAULT 0,
    
    -- Billing and analytics
    billing_units DECIMAL(10,4) DEFAULT 1.0, -- How much this request costs
    user_agent TEXT,
    ip_address INET,
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage quotas and billing
CREATE TABLE IF NOT EXISTS usage_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Usage limits
    api_requests_limit INTEGER NOT NULL,
    gpu_hours_limit INTEGER NOT NULL,
    data_transfer_limit_gb INTEGER NOT NULL,
    
    -- Current usage
    api_requests_used INTEGER DEFAULT 0,
    gpu_hours_used DECIMAL(10,2) DEFAULT 0,
    data_transfer_used_gb DECIMAL(10,2) DEFAULT 0,
    
    -- Billing
    overage_api_rate DECIMAL(10,4) DEFAULT 0.001, -- $0.001 per extra request
    overage_gpu_rate DECIMAL(10,2) DEFAULT 0.50, -- $0.50 per extra GPU hour
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, period_start)
);

-- Billing invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    
    -- Billing period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Amounts
    subscription_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    usage_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    
    -- Payment details
    stripe_invoice_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, failed, cancelled
    paid_at TIMESTAMP,
    due_date DATE NOT NULL,
    
    -- Invoice data
    line_items JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook endpoints for external integrations
CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]', -- Array of event types to send
    secret VARCHAR(255) NOT NULL, -- For webhook signature verification
    is_active BOOLEAN DEFAULT true,
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook delivery logs
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status_code INTEGER,
    response_body TEXT,
    error_message TEXT,
    delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_v2_org_id ON api_keys_v2(organization_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_v2_hash ON api_keys_v2(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_v2_active ON api_keys_v2(is_active);

CREATE INDEX IF NOT EXISTS idx_api_usage_logs_org_id ON api_usage_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_timestamp ON api_usage_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_endpoint ON api_usage_logs(endpoint);

CREATE INDEX IF NOT EXISTS idx_team_members_org_id ON team_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_team_members_email ON team_members(email);

CREATE INDEX IF NOT EXISTS idx_usage_quotas_org_period ON usage_quotas(organization_id, period_start);

CREATE INDEX IF NOT EXISTS idx_invoices_org_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

-- Insert default data
INSERT INTO organizations (id, name, owner_email, plan_type) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Default Organization', 'admin@gpudex.ai', 'enterprise')
ON CONFLICT (id) DO NOTHING;

-- Create a trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
CREATE TRIGGER update_organizations_updated_at 
    BEFORE UPDATE ON organizations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_api_keys_v2_updated_at ON api_keys_v2;
CREATE TRIGGER update_api_keys_v2_updated_at 
    BEFORE UPDATE ON api_keys_v2 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_usage_quotas_updated_at ON usage_quotas;
CREATE TRIGGER update_usage_quotas_updated_at 
    BEFORE UPDATE ON usage_quotas 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
CREATE TRIGGER update_invoices_updated_at 
    BEFORE UPDATE ON invoices 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 