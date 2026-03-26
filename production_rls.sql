-- 1. Lock down the Users table (Users can only see their own private info)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile" 
ON public.users FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" 
ON public.users FOR UPDATE USING (auth.uid() = id);

-- 2. Lock down the Cart (Users can only see their own cart)
ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own cart" 
ON public.cart_items FOR ALL USING (auth.uid() = user_id);

-- 3. Items Table (Everyone can view available items, only owners can edit/delete)
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view available items" 
ON public.items FOR SELECT USING (status = 'Available');

CREATE POLICY "Owners can view and manage their own items" 
ON public.items FOR ALL USING (auth.uid() = owner_id);

-- 4. Orders Table (Only the buyer and seller involved can view the order)
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Buyers and Sellers can view their orders" 
ON public.orders FOR SELECT USING (auth.uid() = buyer_id OR auth.uid() = seller_id);
