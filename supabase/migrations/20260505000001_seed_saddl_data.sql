-- SEED SADDL DATA
-- Sample accounts and BSR history for testing

INSERT INTO public.accounts (account_id, account_name, organization_id)
VALUES 
('acc_001', 'SADDL UAE Main', 'org_saddl'),
('acc_002', 'Kitchen Pro KSA', 'org_saddl'),
('acc_003', 'Beauty Hub Global', 'org_beauty')
ON CONFLICT (account_id) DO NOTHING;

-- Seed BSR History (Today)
INSERT INTO sc_raw.bsr_history (asin, marketplace_id, category_name, rank, report_date)
VALUES 
('B07WSHWNCG', 'acc_001', 'Kitchen & Dining', 45, CURRENT_DATE),
('B08XYY5V6X', 'acc_001', 'Water Bottles', 12, CURRENT_DATE),
('B09Z123456', 'acc_002', 'Home & Kitchen', 150, CURRENT_DATE),
('B0B6789012', 'acc_003', 'Beauty', 8, CURRENT_DATE)
ON CONFLICT DO NOTHING;

-- Seed BSR History (7 days ago to test trends)
INSERT INTO sc_raw.bsr_history (asin, marketplace_id, category_name, rank, report_date)
VALUES 
('B07WSHWNCG', 'acc_001', 'Kitchen & Dining', 50, CURRENT_DATE - INTERVAL '7 days'),
('B08XYY5V6X', 'acc_001', 'Water Bottles', 10, CURRENT_DATE - INTERVAL '7 days'),
('B09Z123456', 'acc_002', 'Home & Kitchen', 140, CURRENT_DATE - INTERVAL '7 days')
ON CONFLICT DO NOTHING;
