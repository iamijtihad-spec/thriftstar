import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Missing Supabase keys in .env file!")
    exit(1)

supabase: Client = create_client(url, key)

def seed_database():
    print("🌱 Seeding Thrift Star Database...")

    # 1. Create Mock Users
    user_data = [
        {"username": "seller_A", "email": "sellerA@thriftstar.mock", "rating": 4.8},
        {"username": "seller_B", "email": "sellerB@thriftstar.mock", "rating": 5.0},
        {"username": "Current_User", "email": "me@thriftstar.mock", "rating": 4.9}
    ]

    print("Inserting Users...")
    users_inserted = []
    for u in user_data:
        # Check if user already exists
        response = supabase.table("users").select("*").eq("username", u["username"]).execute()
        if len(response.data) > 0:
            print(f"   [Skipped] User {u['username']} already exists.")
            users_inserted.append(response.data[0])
        else:
            res = supabase.table("users").insert(u).execute()
            users_inserted.append(res.data[0])
            print(f"   [Added] User {u['username']}")

    # Map usernames to their generated UUIDs
    user_ids = {u["username"]: u["id"] for u in users_inserted}

    # 2. Create Mock Items
    item_data = [
        {"owner_id": user_ids["seller_A"], "brand": "Vintage", "item_name": "90s Nirvana Tee", "price": 150, "size": "L", "image": "https://placehold.co/400x400/1e1e1e/FFF?text=90s+Nirvana+Tee"},
        {"owner_id": user_ids["seller_A"], "brand": "Carhartt", "item_name": "Double Knee Pants", "price": 85, "size": "32x32", "image": "https://placehold.co/400x400/1e1e1e/FFF?text=Carhartt+Pants"},
        {"owner_id": user_ids["seller_B"], "brand": "Arc'teryx", "item_name": "Beta AR Jacket", "price": 350, "size": "M", "image": "https://placehold.co/400x400/1e1e1e/FFF?text=Arcteryx+Jacket"},
        {"owner_id": user_ids["Current_User"], "brand": "Nike", "item_name": "Jordan 1 Chicago", "price": 400, "size": "10", "image": "https://placehold.co/400x400/1e1e1e/FFF?text=Jordan+1"},
        {"owner_id": user_ids["Current_User"], "brand": "Supreme", "item_name": "Box Logo Hoodie", "price": 250, "size": "L", "image": "https://placehold.co/400x400/1e1e1e/FFF?text=Supreme+Bogo"},
    ]

    print("\nInserting Items...")
    for item in item_data:
        # Check if item already exists to prevent duplicates on multiple runs
        response = supabase.table("items").select("*").eq("item_name", item["item_name"]).eq("owner_id", item["owner_id"]).execute()
        
        # NOTE: Our schema uses 'estimated_value_usd' and 'image_url', let's map the naming correctly
        db_item = {
            "owner_id": item["owner_id"],
            "brand": item["brand"],
            "item_name": item["item_name"],
            "size": item["size"],
            "estimated_value_usd": item["price"],
            "image_url": item["image"]
        }
        
        if len(response.data) > 0:
            print(f"   [Skipped] Item {item['item_name']} already exists.")
        else:
            supabase.table("items").insert(db_item).execute()
            print(f"   [Added] Item {item['brand']} {item['item_name']}")

    print("\n✅ Seeding Complete! Your Supabase database is now populated.")

if __name__ == "__main__":
    seed_database()
