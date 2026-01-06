# 会话文件转Pyrogram字符串Session的工具
# 只需修改下面的API_ID和API_HASH，其他不用动
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

# --------------------------需要你修改的地方--------------------------
API_ID = 28325542  # 替换成你自己的API ID（从my.telegram.org获取）
API_HASH = "1f2a42b2ebec2beca6dafe1171994531"  # 替换成你自己的API HASH
SESSION_FILE_NAME = "session_8618588631716.session"  # 你的.session文件名，不用改就留着
# -------------------------------------------------------------------

try:
    # 读取.session文件并转换为字符串Session
    with TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH) as client:
        string_session = StringSession.save(client.session)
    # 输出结果
    print("\n✅ 转换成功！你的Pyrogram字符串Session是：")
    print("====================================================")
    print(string_session)
    print("====================================================")
    print("\n⚠️ 请复制上面这串字符，粘贴到你的项目SESSION配置里！")
except Exception as e:
    print(f"\n❌ 转换失败！错误原因：{str(e)}")
    print("\n🔍 检查这几点：")
    print("1. API_ID/API_HASH是否填对（必须和生成.session文件时用的一致）")
    print("2. .session文件是否和这个脚本放在同一个文件夹里")
    print("3. .session文件名是否和代码里的SESSION_FILE_NAME一致")
