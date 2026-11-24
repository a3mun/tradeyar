-- TradeMun subscription deletion / refund-history migration
-- Target: PostgreSQL 16 (production database)
-- Run once before deploying the updated API code.
BEGIN;

-- Keep the original subscription identifier as an audit reference.
ALTER TABLE refund_requests
    ADD COLUMN IF NOT EXISTS subscription_id_snapshot INTEGER;

UPDATE refund_requests
SET subscription_id_snapshot = subscription_id
WHERE subscription_id_snapshot IS NULL
  AND subscription_id IS NOT NULL;

-- A refund record must survive even after its subscription row is deleted.
ALTER TABLE refund_requests
    ALTER COLUMN subscription_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS ix_refund_requests_subscription_id_snapshot
    ON refund_requests (subscription_id_snapshot);

COMMIT;
