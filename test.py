from db.database import get_database
from datastructure.object import Exchange
db = get_database()
print(db.load_tick_data('rb2305', Exchange('SHFE')))