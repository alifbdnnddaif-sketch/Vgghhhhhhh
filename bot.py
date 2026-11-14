import os
import sqlite3
import zipfile
import requests
import telebot

TOKEN = "8902637263:AAEfkuzqnCK-gEkKOS4d8jBBhzxMJp9ybdo"
bot = telebot.TeleBot(TOKEN)

# Temporary storage API URL yaad rakhne ke liye
user_api_data = {}


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "🤖 **Smart Database Bot Active!**\n\nCommand use karein:\n`/getdb"
      " <API_URL>`",
      parse_mode="Markdown",
  )


# Step 1: User jab /getdb <URL> bhejega
@bot.message_handler(commands=["getdb"])
def ask_count(message):
  try:
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
      bot.reply_to(
          message,
          "❌ Kripya API URL bhi dein.\nExample: `/getdb"
          " https://admin.gbssystems.com/public/gateway/apiv1/api.php?key=9NXZC&cmd=number&query=`",
          parse_mode="Markdown",
      )
      return

    # URL ko save kar lo
    user_api_data[message.chat.id] = parts[1].strip()

    # Bot ab user se puchega kitne numbers ka chahiye
    msg = bot.reply_to(
        message,
        "📊 **Kitne numbers ka data chahiye?**\n(Aap koi number likh sakte hain"
        " jaise `500`, ya phir `all` likh sakte hain)",
        parse_mode="Markdown",
    )
    # Agla message user ka count hoga
    bot.register_next_step_handler(msg, process_database_generation)

  except Exception as e:
    bot.reply_to(message, f"❌ Error: {str(e)}")


# Step 2: User ka count milne ke baad automatic fetching start hogi
def process_database_generation(message):
  try:
    chat_id = message.chat.id
    user_input = message.text.strip().lower()

    if chat_id not in user_api_data:
      bot.reply_to(
          message, "❌ Session expire ho gaya. Dobara `/getdb <URL>` se shuru karein."
      )
      return

    base_url = user_api_data[chat_id]

    # Limit decide karna
    if user_input == "all":
      limit = 1000  # Safety ke liye max limit (ya apne hisab se set karein)
      bot.reply_to(
          message,
          "⚡ **All mode selected!** Saara data automatic fetch ho raha hai..."
          " ⏳",
          parse_mode="Markdown",
      )
    else:
      try:
        limit = int(user_input)
        bot.reply_to(
            message,
            f"⚡ **{limit} numbers** ka data fetch ho raha hai... ⏳",
            parse_mode="Markdown",
        )
      except ValueError:
        bot.reply_to(
            message,
            "❌ Kripya valid number ya 'all' likhein. Dobara `/getdb` se"
            " try karein.",
        )
        return

    db_name = "automatic_records.db"
    if os.path.exists(db_name):
      os.remove(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    table_created = False
    total_fetched = 0
    start_number = 9093614200  # Starting mobile number example

    # Automatic loop jo numbers generate karke fetch karega
    for i in range(limit):
      current_number = start_number + i
      api_url = f"{base_url}{current_number}"

      try:
        response = requests.get(api_url, timeout=3)
        if response.status_code == 200:
          res_data = response.json()

          records = []
          if isinstance(res_data, list):
            records = res_data
          elif isinstance(res_data, dict):
            records = (
                res_data.get("results")
                or res_data.get("data")
                or [res_data]
            )

          if records and isinstance(records[0], dict):
            if not table_created:
              keys = list(records[0].keys())
              columns_def = ", ".join([f'"{key}" TEXT' for key in keys])
              cursor.execute(
                  f"CREATE TABLE IF NOT EXISTS all_records ({columns_def})"
              )
              conn.commit()
              table_created = True

            for item in records:
              keys = list(item.keys())
              values = [str(item.get(key, "")) for key in keys]
              placeholders = ", ".join(["?" for _ in keys])
              cursor.execute(
                  f"INSERT INTO all_records VALUES ({placeholders})", values
              )
            conn.commit()
            total_fetched += 1
      except:
        continue

    conn.close()

    # File check aur sending
    if os.path.exists(db_name) and os.path.getsize(db_name) > 0:
      file_size_mb = os.path.getsize(db_name) / (1024 * 1024)
      file_to_send = db_name
      caption = f"✅ **Database Ready!**\n📊 Total Records: {total_fetched}\n📁 Size: {file_size_mb:.2f} MB"

      # Agar size bada ho toh ZIP banayein
      if file_size_mb > 45:
        zip_name = "automatic_records.zip"
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
          zipf.write(db_name, os.path.basename(db_name))
        file_to_send = zip_name
        zip_size_mb = os.path.getsize(zip_name) / (1024 * 1024)
        caption = f"🗜️ **Compressed ZIP Ready!**\n📦 Size: {zip_size_mb:.2f} MB"

      with open(file_to_send, "rb") as f:
        bot.send_document(
            message.chat.id, f, caption=caption, parse_mode="Markdown"
        )

      # Cleanup
      if os.path.exists(db_name):
        os.remove(db_name)
      if os.path.exists("automatic_records.zip"):
        os.remove("automatic_records.zip")
    else:
      bot.reply_to(
          message, "❌ Koi valid data nahi mila ya database khaali reh gaya."
      )

  except Exception as e:
    bot.reply_to(message, f"❌ Error: {str(e)}")


if __name__ == "__main__":
  print("🤖 Interactive Bot started successfully...")
  bot.infinity_polling()
        
