-- PRICE BENCHMARKING MODULE
-- Initial seed data from PRD v2.

INSERT INTO public.pb_organizations (org_id, name, type)
VALUES
    ('s2c', 'S2C / Zenarise Trading', 'seller'),
    ('bubble-bros', 'Bubble Bros', 'seller'),
    ('oneshot', 'One Shot', 'seller')
ON CONFLICT (org_id) DO NOTHING;

INSERT INTO public.pb_clients (client_id, org_id, name, marketplace, sp_api_profile_id)
VALUES
    ('s2c-uae', 's2c', 'S2C UAE', 'UAE', NULL),
    ('s2c-ksa', 's2c', 'S2C KSA', 'KSA', NULL),
    ('bubble-bros-uae', 'bubble-bros', 'Bubble Bros UAE', 'UAE', NULL),
    ('oneshot-uae', 'oneshot', 'One Shot UAE', 'UAE', NULL)
ON CONFLICT (client_id) DO NOTHING;
