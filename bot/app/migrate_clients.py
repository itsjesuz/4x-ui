import asyncio
import sqlite3

from app.db import Database
from app.xui import XuiClient
from app.settings import load_settings

async def main():
    settings = load_settings()
    db = Database("netfly.db")

    # Get Master Location
    locs = db.list_locations(only_enabled=True)
    if not locs:
        print("No enabled master location found.")
        return
    master_loc = locs[0]
    
    if not master_loc.inbound_ids:
        print(f"Master location '{master_loc.name}' has no inbound_ids set! Please configure inbounds.")
        return

    print(f"Using Master Location: {master_loc.name} with Inbounds: {master_loc.inbound_ids}")

    # Fetch all active orders
    conn = sqlite3.connect("netfly.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status = 'active'")
    active_orders = cur.fetchall()
    conn.close()

    print(f"Found {len(active_orders)} active orders to migrate.")

    async with XuiClient(master_loc.base_url, master_loc.api_token) as xui:
        for order in active_orders:
            email = order["xui_email"]
            if not email:
                continue

            order_id = order["id"]
            tg_user_id = order["user_id"]
            uuid = order["xui_client_uuid"]
            sub_id = order["xui_sub_id"]
            volume_gb = order["volume_gb"]
            duration_days = order["duration_days"]

            print(f"Processing Order #{order_id} ({email})...")

            # Check if client exists on master panel
            existing_client = await xui.find_client(email)

            if existing_client:
                # Client exists on master, just update their inbounds
                try:
                    await xui.update_client(
                        email=email,
                        inbound_ids=master_loc.inbound_ids,
                    )
                    db._conn.execute(
                        "UPDATE orders SET location_id = ?, location_name = ?, updated_at = datetime('now') WHERE id = ?",
                        (master_loc.id, master_loc.name, order_id)
                    )
                    db._conn.commit()
                    print(f"  [SUCCESS] Updated {email} to use all inbounds and updated database location.")
                except Exception as e:
                    print(f"  [ERROR] Failed to update {email}: {e}")
            else:
                # Client does not exist on master, create them
                try:
                    await xui.add_client(
                        email=email,
                        volume_gb=volume_gb,
                        duration_days=duration_days,
                        inbound_ids=master_loc.inbound_ids,
                        tg_user_id=tg_user_id,
                        client_uuid=uuid,
                        sub_id=sub_id,
                    )
                    db._conn.execute(
                        "UPDATE orders SET location_id = ?, location_name = ?, updated_at = datetime('now') WHERE id = ?",
                        (master_loc.id, master_loc.name, order_id)
                    )
                    db._conn.commit()
                    print(f"  [SUCCESS] Created {email} on Master Panel and updated database location.")
                except Exception as e:
                    print(f"  [ERROR] Failed to create {email}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
