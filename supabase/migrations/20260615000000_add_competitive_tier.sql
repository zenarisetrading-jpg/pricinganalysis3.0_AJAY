ALTER TABLE pb_client_listings
    ADD COLUMN IF NOT EXISTS competitive_tier TEXT
    CHECK (competitive_tier IN ('Budget', 'Value', 'Mid-Market', 'Premium') OR competitive_tier IS NULL);
