'''
dolphindb脚本创建数据库和数据表
'''

# 创建tick数据库--存储tick数据--按日分区
CREATE_TICK_DATABASE_SCRIPT = '''
dataPath = "dfs://tick_db"
db = database(dataPath, VALUE, 2010.01.01..2030.01.01, engine=`TSDB)
'''

# 创建tick数据表--存储tick数据--按日分区
CREATE_TICK_TABLE_SCRIPT = '''
dataPath = "dfs://tick_db"
db = database(dataPath)

tick_columns = ["symbol", "exchange", "datetime", "volume", "turnover", "open_interest", "last_price", "highest_price", "lowest_price", "bid_price_1", 
"ask_price_1", "bid_volume_1", "ask_volume_1"]
tick_type = [SYMBOL, SYMBOL, NANOTIMESTAMP, LONG, FLOAT, LONG, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, LONG, LONG]
tick = table(100:0, tick_columns, tick_type)

db.createPartitionedTable(tick, "tick", partitionColumns=["datetime"], sortColumns=["symbol", "exchange", "datetime"], keepDuplicates=LAST)
'''

# 创建tickoverview数据表
CREATE_TICKOVERVIEW_TABLE_SCRIPT = '''
dataPath = "dfs://tick_db"
db = database(dataPath)

overview_columns = ["symbol", "exchange", "count", "start", "end", "datetime"]
overview_type = [SYMBOL, SYMBOL, INT, NANOTIMESTAMP, NANOTIMESTAMP, NANOTIMESTAMP]
tickoverview = table(1:0, overview_columns, overview_type)
db.createPartitionedTable(tickoverview, "tickoverview", partitionColumns=["datetime"], sortColumns=["symbol", "exchange", "datetime"], keepDuplicates=LAST)
'''

# 创建contractinfo数据表