import os
import time
import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 导入配置
from main import API_ID, API_HASH, SESSION, BOT_TOKEN, AUTH, FORCESUB, CHECKIN_GROUP, POINTS_PER_CHECKIN, MIN_POINTS

# 初始化机器人
app = Client(
    "SaveRestrictedContentBot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
    bot_token=BOT_TOKEN
)

# 初始化SQLite数据库（存储积分、签到时间）
def init_db():
    conn = sqlite3.connect("user_points.db")
    c = conn.cursor()
    # 创建用户表：user_id（用户ID）、points（积分）、last_checkin（最后签到时间）
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, last_checkin TEXT)''')
    conn.commit()
    conn.close()

# 检查用户是否订阅了指定频道
def check_subscription(user_id):
    if not FORCESUB:
        return True  # 未设置强制订阅则直接通过
    try:
        member = app.get_chat_member(f"@{FORCESUB}", user_id)
        # 检查是否是订阅状态（不是封禁/未加入）
        return member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"订阅检查失败：{e}")
        return False

# 获取用户积分
def get_user_points(user_id):
    conn = sqlite3.connect("user_points.db")
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

# 更新用户积分
def update_user_points(user_id, points):
    conn = sqlite3.connect("user_points.db")
    c = conn.cursor()
    # 存在则更新，不存在则插入
    c.execute("INSERT OR REPLACE INTO users (user_id, points) VALUES (?, COALESCE((SELECT points FROM users WHERE user_id=?), 0) + ?)",
              (user_id, user_id, points))
    conn.commit()
    conn.close()

# 检查用户是否已签到（每日一次）
def check_checkin_status(user_id):
    conn = sqlite3.connect("user_points.db")
    c = conn.cursor()
    c.execute("SELECT last_checkin FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    if not result:
        return False  # 从未签到
    # 对比日期（只看年月日）
    last_checkin = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S").date()
    today = datetime.now().date()
    return last_checkin == today

# 更新用户签到时间
def update_checkin_time(user_id):
    conn = sqlite3.connect("user_points.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO users (user_id, last_checkin) VALUES (?, ?)", (user_id, now))
    conn.commit()
    conn.close()

# 命令1：/start 欢迎语+检查订阅
@app.on_message(filters.command("start") & filters.private)
async def start(_, message):
    user_id = message.from_user.id
    # 检查订阅
    if not check_subscription(user_id):
        subscribe_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 点击订阅频道", url=f"https://t.me/{FORCESUB}")],
            [InlineKeyboardButton("✅ 已订阅，刷新", callback_data="refresh")]
        ])
        await message.reply("⚠️ 请先订阅我的频道才能使用机器人！", reply_markup=subscribe_btn)
        return
    # 发送欢迎语+积分信息
    points = get_user_points(user_id)
    await message.reply(f"""
🎉 欢迎使用受限内容下载机器人！
👉 使用说明：发送受限频道/群的内容链接即可下载
📌 规则：
   1. 每日在指定群发送 /签到 可获得 {POINTS_PER_CHECKIN} 积分
   2. 使用机器人需至少 {MIN_POINTS} 积分
   3. 积分不足请先签到哦！
💡 当前积分：{points}
""")

# 回调按钮：刷新订阅状态
@app.on_callback_query(filters.regex("refresh"))
async def refresh_sub(_, query):
    user_id = query.from_user.id
    if check_subscription(user_id):
        points = get_user_points(user_id)
        await query.edit_message_text(f"""
✅ 订阅成功！
💡 当前积分：{points}
👉 发送受限内容链接即可下载（需至少 {MIN_POINTS} 积分）
""")
    else:
        await query.answer("❌ 你还没订阅频道哦！", show_alert=True)

# 命令2：/签到（仅指定群可用，每日一次）
@app.on_message(filters.command("签到") & filters.chat(CHECKIN_GROUP))
async def checkin(_, message):
    user_id = message.from_user.id
    # 检查是否已签到
    if check_checkin_status(user_id):
        await message.reply("❌ 你今天已经签到过了，明天再来吧！")
        return
    # 增加积分
    update_user_points(user_id, POINTS_PER_CHECKIN)
    update_checkin_time(user_id)
    new_points = get_user_points(user_id)
    await message.reply(f"✅ 签到成功！获得 {POINTS_PER_CHECKIN} 积分，当前总积分：{new_points}")

# 命令3：/积分（查看自己的积分）
@app.on_message(filters.command("积分") & filters.private)
async def my_points(_, message):
    user_id = message.from_user.id
    points = get_user_points(user_id)
    await message.reply(f"💡 你的当前积分：{points}")

# 命令4：/加积分（管理员专用，格式：/加积分 @用户名 数量 或 /加积分 用户ID 数量）
@app.on_message(filters.command("加积分") & filters.user(AUTH))
async def add_points(_, message):
    try:
        # 解析参数
        args = message.text.split()[1:]
        if len(args) < 2:
            await message.reply("❌ 格式错误！正确格式：/加积分 @用户名 数量 或 /加积分 用户ID 数量")
            return
        target = args[0]
        points = int(args[1])
        # 获取目标用户ID
        if target.startswith("@"):
            user = await app.get_users(target)
            target_id = user.id
        else:
            target_id = int(target)
        # 更新积分
        update_user_points(target_id, points)
        new_points = get_user_points(target_id)
        await message.reply(f"✅ 成功给用户 {target} 增加 {points} 积分，该用户当前积分：{new_points}")
    except Exception as e:
        await message.reply(f"❌ 操作失败：{e}")

# 命令5：/info（获取群/用户ID，方便配置）
@app.on_message(filters.command("info"))
async def get_info(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await message.reply(f"""
📌 信息查询：
👤 你的ID：{user_id}
🏘️ 本群ID：{chat_id}
""")

# 核心功能：处理下载请求（受限内容链接）
@app.on_message(filters.private & ~filters.command(["start", "积分"]))
async def download_content(_, message):
    user_id = message.from_user.id
    # 1. 检查订阅
    if not check_subscription(user_id):
        subscribe_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 点击订阅频道", url=f"https://t.me/{FORCESUB}")],
            [InlineKeyboardButton("✅ 已订阅，刷新", callback_data="refresh")]
        ])
        await message.reply("⚠️ 请先订阅我的频道才能使用机器人！", reply_markup=subscribe_btn)
        return
    # 2. 检查积分
    points = get_user_points(user_id)
    if points < MIN_POINTS:
        await message.reply(f"❌ 你的积分不足（当前：{points}，需至少 {MIN_POINTS}）！请先到指定群发送 /签到 获取积分。")
        return
    
    # 3. 处理下载（原核心逻辑）
    try:
        text = message.text
        if "t.me/" not in text:
            await message.reply("❌ 请发送有效的Telegram链接（比如 t.me/b/bot_username/message_id）！")
            return
        
        # 扣1积分（可选，如需使用扣积分则打开下面注释）
        # update_user_points(user_id, -1)
        
        # 解析链接并下载
        await message.reply("⏳ 正在处理，请稍等...")
        if "t.me/b/" in text:
            msg_id = int(text.split("/")[-1])
            bot_un = text.split("/")[-2]
            await app.copy_message(message.chat.id, f"@{bot_un}", msg_id)
        else:
            if "/" in text:
                link = text.split("/")
                chat = link[-2]
                msg_id = int(link[-1])
                await app.copy_message(message.chat.id, chat, msg_id)
        await message.reply("✅ 下载成功！")
        
    except FloodWait as e:
        await message.reply(f"⚠️ 操作太频繁，等待 {e.value} 秒后重试！")
        time.sleep(e.value)
    except Exception as e:
        await message.reply(f"❌ 下载失败：{str(e)}")

# 启动机器人
if __name__ == "__main__":
    init_db()
    print("🤖 机器人已启动！")
    app.run()
