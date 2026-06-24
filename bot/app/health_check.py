import asyncio
import logging
from app.db import Database
from app.xui import XuiClient, XuiError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('health_check')

async def check_health(db_path: str = 'netfly.db'):
    log.info('Starting Health Check...')
    db = Database(db_path)
    
    # 1. Check locations
    locations = db.list_locations()
    log.info(f'Found {len(locations)} locations.')
    for loc in locations:
        if loc.enabled:
            log.info(f'Checking Location {loc.id}: {loc.name}...')
            try:
                async with XuiClient(loc.base_url, loc.api_token) as xui:
                    # try a simple get
                    res = await xui._get('/panel/api/inbounds/list')
                    if res.get('success'):
                        log.info(f'  [OK] Location {loc.id} connected successfully.')
                    else:
                        log.error(f'  [FAIL] Location {loc.id} returned unsuccessful response.')
            except Exception as e:
                log.error(f'  [FAIL] Location {loc.id} connection failed: {e}')
        else:
            log.info(f'Skipping Location {loc.id} (Disabled).')

    # 2. Check Orders missing users
    with db._cursor() as cur:
        cur.execute('SELECT count(*) FROM orders WHERE user_id NOT IN (SELECT user_id FROM users)')
        missing = cur.fetchone()[0]
        if missing > 0:
            log.warning(f'Found {missing} orders pointing to missing users.')
        else:
            log.info('[OK] No orphaned orders found.')
            
    log.info('Health Check Completed.')

if __name__ == '__main__':
    asyncio.run(check_health())
