-- Seed Data for Thrift Star MVP (V2 - Professional Schema)

-- Clear existing mock data if re-running
DELETE FROM public.swap_proposals;
DELETE FROM public.messages;
DELETE FROM public.items;
DELETE FROM public.users;

-- 1. Insert Mock Users (Added paypal_account as requested by the schema)
INSERT INTO public.users (id, username, email, rating, paypal_account)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'seller_A', 'sellerA@thriftstar.mock', 4.8, 'payA@thriftstar.mock'),
  ('22222222-2222-2222-2222-222222222222', 'seller_B', 'sellerB@thriftstar.mock', 5.0, 'payB@thriftstar.mock'),
  ('33333333-3333-3333-3333-333333333333', 'Current_User', 'me@thriftstar.mock', 4.9, 'my_paypal@thriftstar.mock');

-- 2. Insert Mock Items (Updated to fulfill all new column requirements)
INSERT INTO public.items (
    owner_id, 
    photos, 
    listing_title, 
    brand, 
    category, 
    size, 
    condition, 
    color, 
    description, 
    measurements, 
    price, 
    retail_price, 
    listing_tags, 
    shipping_cost, 
    accepts_offers, 
    status
)
VALUES
  -- seller_A's items
  (
      '11111111-1111-1111-1111-111111111111', 
      ARRAY['https://placehold.co/400x400/1e1e1e/FFF?text=90s+Nirvana+Tee'], 
      'Original 90s Nirvana Smiley Tee', 
      'Vintage', 
      'Tops', 
      'L', 
      'Used', 
      'Black', 
      'Incredible fade, single stitched all around. Tiny pinhole near the bottom hem but adds to the character.', 
      '{"pit_to_pit": 22.5, "length": 29}', 
      150.00, 
      NULL, 
      ARRAY['#nirvana', '#vintage', '#bandtee', '#grunge'], 
      5.00, 
      true, 
      'Available'
  ),
  (
      '11111111-1111-1111-1111-111111111111', 
      ARRAY['https://placehold.co/400x400/1e1e1e/FFF?text=Carhartt+Pants'], 
      'Carhartt Double Knee Work Pants', 
      'Carhartt', 
      'Bottoms', 
      '32x32', 
      'Very Worn', 
      'Brown', 
      'Beautifully thrashed and faded double knees. Exact true 32 waist. Some paint splatters.', 
      '{"waist_flat": 16, "inseam": 31, "leg_opening": 9}', 
      85.00, 
      79.99, 
      ARRAY['#carharttdoubleknee', '#workwear', '#faded'], 
      10.00, 
      true, 
      'Available'
  ),
  
  -- seller_B's items
  (
      '22222222-2222-2222-2222-222222222222', 
      ARRAY['https://placehold.co/400x400/1e1e1e/FFF?text=Arcteryx+Jacket'], 
      'Arc''teryx Beta AR Jacket', 
      'Arc''teryx', 
      'Outerwear', 
      'M', 
      'Gently Used', 
      'Black', 
      'Barely worn, Gore-tex still fully beads water. No delamination.', 
      '{"pit_to_pit": 23, "length": 28}', 
      350.00, 
      600.00, 
      ARRAY['#gorpcore', '#arcteryx', '#betaar', '#goretex'], 
      15.00, 
      false, 
      'Available'
  ),

  -- Current_User's items
  (
      '33333333-3333-3333-3333-333333333333', 
      ARRAY['https://placehold.co/400x400/1e1e1e/FFF?text=Jordan+1'], 
      'Jordan 1 Retro High Chicago (2015)', 
      'Nike', 
      'Sneakers', 
      '10', 
      'Gently Used', 
      'Red/White/Black', 
      'Excellent condition. Worn handful of times. Comes with OG box and extra laces. Minimal star loss on toe.', 
      '{}', 
      400.00, 
      160.00, 
      ARRAY['#jordan1', '#chicago', '#sneakerhead'], 
      20.00, 
      true, 
      'Available'
  ),
  (
      '33333333-3333-3333-3333-333333333333', 
      ARRAY['https://placehold.co/400x400/1e1e1e/FFF?text=Supreme+Bogo'], 
      'Supreme Box Logo Hoodie FW21', 
      'Supreme', 
      'Tops', 
      'L', 
      'New', 
      'Charcoal', 
      'Deadstock in plastic. Perfect condition.', 
      '{"pit_to_pit": 24, "length": 29}', 
      250.00, 
      168.00, 
      ARRAY['#supreme', '#bogo', '#streetwear'], 
      10.00, 
      true, 
      'Available'
  );
