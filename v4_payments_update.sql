-- V4 Payments & Payouts Schema Update (Run this once to upgrade your database!)

-- 1. Add a PayPal routing email to the Users table so sellers can get paid
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS paypal_email TEXT;
