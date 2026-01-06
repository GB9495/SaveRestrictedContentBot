import os

# 基础配置
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION = os.environ.get("SESSION", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
AUTH = int(os.environ.get("AUTH", 0))  # 管理员ID
FORCESUB = os.environ.get("FORCESUB", "")  # 强制订阅频道（不带@）

# 积分&签到配置
CHECKIN_GROUP = int(os.environ.get("CHECKIN_GROUP", 0))  # 签到群ID
POINTS_PER_CHECKIN = int(os.environ.get("POINTS_PER_CHECKIN", 5))  # 每次签到积分
MIN_POINTS = int(os.environ.get("MIN_POINTS", 1))  # 使用机器人最低积分
