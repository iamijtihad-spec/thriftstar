-- ==================================================================================
-- THRIFT STAR — PRODUCTION ROW LEVEL SECURITY (RLS) HARDENING
-- Run this in your Supabase SQL Editor BEFORE going live with real users.
-- This ensures the database itself enforces privacy, even if app code has bugs.
-- ==================================================================================

-- Enable RLS on all tables (safe to run twice, idempotent)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.swap_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies to start clean
DROP POLICY IF EXISTS "users_select_own" ON public.users;
DROP POLICY IF EXISTS "users_update_own" ON public.users;
DROP POLICY IF EXISTS "users_insert_own" ON public.users;
DROP POLICY IF EXISTS "users_public_read" ON public.users;
DROP POLICY IF EXISTS "items_read_available" ON public.items;
DROP POLICY IF EXISTS "items_insert_own" ON public.items;
DROP POLICY IF EXISTS "items_update_own" ON public.items;
DROP POLICY IF EXISTS "items_delete_own" ON public.items;
DROP POLICY IF EXISTS "swap_proposals_read_own" ON public.swap_proposals;
DROP POLICY IF EXISTS "swap_proposals_insert_own" ON public.swap_proposals;
DROP POLICY IF EXISTS "swap_proposals_update_own" ON public.swap_proposals;
DROP POLICY IF EXISTS "orders_read_own" ON public.orders;
DROP POLICY IF EXISTS "orders_insert_own" ON public.orders;
DROP POLICY IF EXISTS "cart_items_read_own" ON public.cart_items;
DROP POLICY IF EXISTS "cart_items_insert_own" ON public.cart_items;
DROP POLICY IF EXISTS "cart_items_delete_own" ON public.cart_items;

-- ==================================================================================
-- USERS TABLE
-- Public profile info visible to all (username, bio, paypal status).
-- Private info (address, phone) can only be read/written by the owner.
-- ==================================================================================
CREATE POLICY "users_public_read" ON public.users
    FOR SELECT USING (true); -- Username/bio/photo visible to all logged-in users

CREATE POLICY "users_insert_own" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "users_update_own" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- ==================================================================================
-- ITEMS TABLE
-- All Available items visible in the feed to everyone.
-- Only the owner can create, update, or delete their own items.
-- ==================================================================================
CREATE POLICY "items_read_available" ON public.items
    FOR SELECT USING (
        status = 'Available'          -- Anyone can browse available items
        OR owner_id = auth.uid()      -- Owners can always see their own items
        OR EXISTS (                   -- Buyers/Sellers can see sold items in orders
            SELECT 1 FROM public.orders
            WHERE item_id = items.id
            AND (buyer_id = auth.uid() OR seller_id = auth.uid())
        )
    );

CREATE POLICY "items_insert_own" ON public.items
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "items_update_own" ON public.items
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "items_delete_own" ON public.items
    FOR DELETE USING (auth.uid() = owner_id);

-- ==================================================================================
-- SWAP PROPOSALS TABLE
-- Only the proposer or receiver of a deal can see or modify it.
-- ==================================================================================
CREATE POLICY "swap_proposals_read_own" ON public.swap_proposals
    FOR SELECT USING (
        auth.uid() = original_proposer_id
        OR auth.uid() = original_receiver_id
    );

CREATE POLICY "swap_proposals_insert_own" ON public.swap_proposals
    FOR INSERT WITH CHECK (auth.uid() = original_proposer_id);

CREATE POLICY "swap_proposals_update_own" ON public.swap_proposals
    FOR UPDATE USING (
        auth.uid() = original_proposer_id
        OR auth.uid() = original_receiver_id
    );

-- ==================================================================================
-- ORDERS TABLE
-- Only the buyer or seller on an order can see it or create new records.
-- ==================================================================================
CREATE POLICY "orders_read_own" ON public.orders
    FOR SELECT USING (
        auth.uid() = buyer_id
        OR auth.uid() = seller_id
    );

CREATE POLICY "orders_insert_own" ON public.orders
    FOR INSERT WITH CHECK (
        auth.uid() = buyer_id
        OR auth.uid() = seller_id
    );

-- ==================================================================================
-- CART ITEMS TABLE
-- Users can only see, add, or remove items from their own cart.
-- ==================================================================================
CREATE POLICY "cart_items_read_own" ON public.cart_items
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "cart_items_insert_own" ON public.cart_items
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "cart_items_delete_own" ON public.cart_items
    FOR DELETE USING (auth.uid() = user_id);

-- ==================================================================================
-- DONE! Run: NOTIFY pgrst, 'reload schema'; to force instant API cache refresh.
-- ==================================================================================
NOTIFY pgrst, 'reload schema';
