import os
import traceback
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    MessageOriginUser
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError, Forbidden, BadRequest

# ===============================
# CONFIG
# ===============================
TOKEN = "8292810744:AAGTYsSiIU_cnRRNjG2JIKznxowTt7_x4Ds"  # Replace with your real bot token from BotFather
ADMIN_CHAT_ID = 7350047143
VIDEO_FILE = "circle.mp4"
BACKUP_GROUP_LINK = "https://t.me/yourbackupgroup"  # Updated to backup group link
WELCOME_MESSAGE = "🎉 Welcome, {user_first_name}!"

# Persistent storage for users and config
users = set()  # Active users
blocked_users = set()  # Blocked users
config = {
    "welcome_message": WELCOME_MESSAGE,
    "video_file": VIDEO_FILE,
    "backup_group_link": BACKUP_GROUP_LINK
}

# ===============================
# WELCOME HANDLER
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command and send welcome message and video."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    users.add(chat_id)
    blocked_users.discard(chat_id)  # Remove from blocked if they start again

    keyboard = [
        [InlineKeyboardButton("✨ Visit Backup Group", url=config["backup_group_link"])],
        [InlineKeyboardButton("📩 Contact Admin", url=f"tg://user?id={ADMIN_CHAT_ID}")],
    ]

    # Send welcome message
    try:
        welcome_msg = await update.message.reply_text(
            config["welcome_message"].format(user_first_name=user.first_name),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Store welcome message ID
        if chat_id not in context.user_data:
            context.user_data[chat_id] = {'bot_messages': []}
        context.user_data[chat_id]['bot_messages'].append(welcome_msg.message_id)
    except Forbidden:
        print(f"User {chat_id} has blocked the bot.")
        users.discard(chat_id)
        blocked_users.add(chat_id)
        return

    # Send video note if exists
    if os.path.exists(config["video_file"]):
        try:
            with open(config["video_file"], "rb") as video:
                video_msg = await context.bot.send_video_note(
                    chat_id,
                    video,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                context.user_data[chat_id]['bot_messages'].append(video_msg.message_id)
        except Forbidden:
            print(f"User {chat_id} has blocked the bot during video send.")
            users.discard(chat_id)
            blocked_users.add(chat_id)
        except TelegramError as e:
            print(f"Failed to send video note to {chat_id}: {e}")

# ===============================
# STATS COMMAND
# ===============================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display detailed bot statistics for admin, including subscribed and blocked users."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Only admins can use this command.")
        return
    subscribed_count = len(users)
    blocked_count = len(blocked_users)
    total_interactions = subscribed_count + blocked_count
    subscribed_list = "\n".join([f"User ID: {uid}" for uid in sorted(users)]) or "No subscribed users."
    blocked_list = "\n".join([f"User ID: {uid}" for uid in sorted(blocked_users)]) or "No blocked users."

    stats_message = (
        f"📊 Bot Statistics:\n\n"
        f"👥 Subscribed Users: {subscribed_count}\n"
        f"🚫 Blocked Users: {blocked_count}\n"
        f"📈 Total Interactions: {total_interactions}\n\n"
        f"📋 Subscribed Users List:\n{subscribed_list}\n\n"
        f"🚫 Blocked Users List:\n{blocked_list}\n\n"
        f"ℹ️ Note: Blocked users are detected when they block the bot after starting."
    )
    await update.message.reply_text(stats_message)

# ===============================
# ADMIN MENU
# ===============================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin menu with broadcast subsection and stats option."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    chat_id = update.effective_chat.id

    # Delete previous bot messages for admin
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"Admin {chat_id} has blocked the bot during message deletion.")
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast Options", callback_data="broadcast_menu")],
        [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="edit_welcome_message")],
        [InlineKeyboardButton("🎞️ Edit Welcome Video", callback_data="edit_welcome_video")],
        [InlineKeyboardButton("🔗 Edit Backup Group Link", callback_data="edit_backup_group_link")],
        [InlineKeyboardButton("📊 Show Stats", callback_data="show_stats")]
    ]
    menu_text = "⚙️ Admin Menu: What do you want to do?"
    if update.callback_query:
        await update.callback_query.edit_message_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg = await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data[chat_id]['bot_messages'].append(msg.message_id)

# --- Broadcast Menu ---
async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display broadcast options submenu."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    # Delete previous bot messages for admin
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"Admin {chat_id} has blocked the bot during message deletion.")
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

    keyboard = [
        [InlineKeyboardButton("📝 Add Text", callback_data="add_text")],
        [InlineKeyboardButton("📸 Add Photo", callback_data="add_photo")],
        [InlineKeyboardButton("🎥 Add Video", callback_data="add_video")],
        [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
        [InlineKeyboardButton("✅ Publish", callback_data="publish"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]
    ]
    await q.edit_message_text("📢 Broadcast Options: What do you want to prepare?", reply_markup=InlineKeyboardMarkup(keyboard))

# ===============================
# BROADCAST HANDLER
# ===============================
# --- Broadcast: Add Text ---
async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add text for broadcast."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "text"
    await q.edit_message_text("✍️ Send me the text message.")

# --- Broadcast: Add Photo ---
async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a photo for broadcast."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "photo"
    await q.edit_message_text("📸 Send me the photo.")

# --- Broadcast: Add Video ---
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a video for broadcast."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "video"
    await q.edit_message_text("🎥 Send me the video.")

# --- Broadcast: Add Button ---
async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a button for broadcast."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "button"
    await q.edit_message_text("➕ Send button in format: Text|https://link")

# --- Broadcast: Publish ---
async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all subscribed users."""
    q = update.callback_query
    await q.answer()
    text = context.user_data.get('text')
    photo = context.user_data.get('photo')
    video = context.user_data.get('video')
    buttons = context.user_data.get('buttons', [])
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(t, url=u)] for t, u in buttons]) if buttons else None

    chat_id = update.effective_chat.id
    # Delete previous bot messages for admin
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"Admin {chat_id} has blocked the bot during message deletion.")
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

    recipients = users - {ADMIN_CHAT_ID}
    failed = 0
    for uid in recipients:
        try:
            if video:
                msg = await context.bot.send_video(uid, video, caption=text or "", reply_markup=markup)
            elif photo:
                msg = await context.bot.send_photo(uid, photo, caption=text or "", reply_markup=markup)
            elif text:
                msg = await context.bot.send_message(uid, text, reply_markup=markup)
            # Store broadcast message ID
            if uid not in context.user_data:
                context.user_data[uid] = {'bot_messages': []}
            context.user_data[uid]['bot_messages'].append(msg.message_id)
        except Forbidden:
            print(f"User {uid} has blocked the bot.")
            users.discard(uid)
            blocked_users.add(uid)
            failed += 1
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            failed += 1

    msg = await q.edit_message_text(f"✅ Broadcast sent to {len(recipients)-failed}/{len(recipients)} users")
    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    context.user_data.clear()

# --- Broadcast: Cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current broadcast operation."""
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text("❌ Cancelled.")

# ===============================
# WELCOME CONFIGURATION
# ===============================
async def edit_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of welcome message."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "welcome_message"
    await q.edit_message_text("✍️ Send the new welcome message.")

async def edit_welcome_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of welcome video."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "welcome_video"
    await q.edit_message_text("🎞️ Send the new welcome video file (or type 'remove' to clear).")

# ===============================
# BACKUP GROUP LINK CONFIGURATION
# ===============================
async def edit_backup_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of backup group link."""
    q = update.callback_query
    await q.answer()
    context.user_data['awaiting'] = "backup_group_link"
    await q.edit_message_text("🔗 Send the new backup group link (e.g., https://t.me/yourbackupgroup).")

# ===============================
# STATS HANDLER
# ===============================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display stats via menu callback."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    # Delete previous bot messages for admin
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"Admin {chat_id} has blocked the bot during message deletion.")
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

    subscribed_count = len(users)
    blocked_count = len(blocked_users)
    total_interactions = subscribed_count + blocked_count
    subscribed_list = "\n".join([f"User ID: {uid}" for uid in sorted(users)]) or "No subscribed users."
    blocked_list = "\n".join([f"User ID: {uid}" for uid in sorted(blocked_users)]) or "No blocked users."

    stats_message = (
        f"📊 Bot Statistics:\n\n"
        f"👥 Subscribed Users: {subscribed_count}\n"
        f"🚫 Blocked Users: {blocked_count}\n"
        f"📈 Total Interactions: {total_interactions}\n\n"
        f"📋 Subscribed Users List:\n{subscribed_list}\n\n"
        f"🚫 Blocked Users List:\n{blocked_list}\n\n"
        f"ℹ️ Note: Blocked users are detected when they block the bot after starting."
    )
    msg = await q.edit_message_text(stats_message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]]))
    context.user_data[chat_id]['bot_messages'].append(msg.message_id)

# ===============================
# ADMIN INPUT HANDLERS
# ===============================
async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin inputs for broadcast, welcome, and backup group link."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    # Skip if this is a reply message (let reply_from_admin handle it)
    if update.message.reply_to_message:
        return

    chat_id = update.effective_chat.id
    # Delete previous bot messages for admin
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"Admin {chat_id} has blocked the bot during message deletion.")
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

    awaiting = context.user_data.get('awaiting')
    if not awaiting:
        return

    success = False
    if awaiting == "text" and update.message.text:
        context.user_data['text'] = update.message.text
        msg = await update.message.reply_text("✅ Text saved.")
        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        success = True
    elif awaiting == "photo" and update.message.photo:
        context.user_data['photo'] = update.message.photo[-1].file_id
        msg = await update.message.reply_text("✅ Photo saved.")
        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        success = True
    elif awaiting == "video" and update.message.video:
        context.user_data['video'] = update.message.video.file_id
        msg = await update.message.reply_text("✅ Video saved.")
        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        success = True
    elif awaiting == "button" and update.message.text:
        try:
            text, url = update.message.text.split("|", 1)
            if 'buttons' not in context.user_data:
                context.user_data['buttons'] = []
            context.user_data['buttons'].append((text.strip(), url.strip()))
            msg = await update.message.reply_text(f"✅ Button [{text.strip()}] added.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        except:
            msg = await update.message.reply_text("⚠️ Invalid format. Use: Text|https://link")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    elif awaiting == "welcome_message" and update.message.text:
        config['welcome_message'] = update.message.text
        msg = await update.message.reply_text("✅ Welcome message updated.")
        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        success = True
    elif awaiting == "welcome_video":
        if update.message.text and update.message.text.lower().strip() == "remove":
            config['video_file'] = ""
            msg = await update.message.reply_text("✅ Welcome video removed.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        elif update.message.video:
            file = await update.message.video.get_file()
            file_path = f"welcome_video_{update.message.video.file_id}.mp4"
            await file.download_to_drive(file_path)
            config['video_file'] = file_path
            msg = await update.message.reply_text("✅ Welcome video updated.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        else:
            msg = await update.message.reply_text("⚠️ Please send a video file or type 'remove'.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    elif awaiting == "backup_group_link" and update.message.text:
        if update.message.text.startswith("https://t.me/"):
            config['backup_group_link'] = update.message.text
            msg = await update.message.reply_text("✅ Backup group link updated.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        else:
            msg = await update.message.reply_text("⚠️ Please send a valid Telegram backup group link (e.g., https://t.me/yourbackupgroup).")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)

    if success:
        context.user_data['awaiting'] = None
        if awaiting in ["text", "photo", "video", "button"]:
            await broadcast_menu(update, context)
        else:
            await menu(update, context)

# ===============================
# USER → ADMIN FORWARD / ADMIN REPLY
# ===============================
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user messages to admin, delete previous bot messages, and provide feedback."""
    if update.effective_chat.id == ADMIN_CHAT_ID:
        return
    if update.message.text and update.message.text.lower().strip() == "hello":
        try:
            hello_msg = await update.message.reply_text("Hello! How can I assist you?")
            chat_id = update.effective_chat.id
            if chat_id not in context.user_data:
                context.user_data[chat_id] = {'bot_messages': []}
            context.user_data[chat_id]['bot_messages'].append(hello_msg.message_id)
        except Forbidden:
            print(f"User {update.effective_chat.id} has blocked the bot.")
            users.discard(update.effective_chat.id)
            blocked_users.add(update.effective_chat.id)
        return
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Delete previous bot messages
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except BadRequest:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: Message may have been already deleted.")
            except Forbidden:
                print(f"User {chat_id} has blocked the bot during message deletion.")
                users.discard(chat_id)
                blocked_users.add(chat_id)
                return
            except TelegramError as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []  # Clear the list after deletion

    try:
        # Forward the message to admin
        fwd = await update.message.forward(ADMIN_CHAT_ID)
        # Send feedback to user
        feedback_msg = await update.message.reply_text("📬 Message sent to admin.")
        # Store feedback message ID
        if chat_id not in context.user_data:
            context.user_data[chat_id] = {'bot_messages': []}
        context.user_data[chat_id]['bot_messages'].append(feedback_msg.message_id)
    except Forbidden:
        print(f"User {chat_id} has blocked the bot.")
        users.discard(chat_id)
        blocked_users.add(chat_id)
    except TelegramError as e:
        print(f"Failed to forward message from {chat_id}: {e}")
        await update.message.reply_text("⚠️ Failed to send your message. Please try again.")

async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin replies to users and store reply message IDs."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    if not update.message.reply_to_message:
        return
    replied_msg = update.message.reply_to_message
    if replied_msg.forward_origin and isinstance(replied_msg.forward_origin, MessageOriginUser):
        target_id = replied_msg.forward_origin.sender_user.id
    else:
        await update.message.reply_text("⚠️ Please reply to a forwarded user message.")
        return
    try:
        if update.message.text:
            reply_msg = await context.bot.send_message(target_id, update.message.text)
            await update.message.reply_text("✅ Reply sent to the user.")
        elif update.message.photo:
            reply_msg = await context.bot.send_photo(target_id, update.message.photo[-1].file_id, caption=update.message.caption or "")
            await update.message.reply_text("✅ Photo reply sent to the user.")
        elif update.message.video:
            reply_msg = await context.bot.send_video(target_id, update.message.video.file_id, caption=update.message.caption or "")
            await update.message.reply_text("✅ Video reply sent to the user.")
        # Store reply message ID
        if target_id not in context.user_data:
            context.user_data[target_id] = {'bot_messages': []}
        context.user_data[target_id]['bot_messages'].append(reply_msg.message_id)
    except Forbidden:
        print(f"User {target_id} has blocked the bot.")
        users.discard(target_id)
        blocked_users.add(target_id)
        await update.message.reply_text("⚠️ The user has blocked the bot.")
    except TelegramError as e:
        print(f"Failed to send reply to {target_id}: {e}")
        await update.message.reply_text(f"⚠️ Failed to send reply: {e}")

# ===============================
# BROADCAST CALLBACK HANDLER
# ===============================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers."""
    q = update.callback_query
    data = q.data

    if data == "broadcast_menu":
        await broadcast_menu(update, context)
    elif data == "add_text":
        await add_text(update, context)
    elif data == "add_photo":
        await add_photo(update, context)
    elif data == "add_video":
        await add_video(update, context)
    elif data == "add_button":
        await add_button(update, context)
    elif data == "publish":
        await publish(update, context)
    elif data == "cancel":
        await cancel(update, context)
    elif data == "edit_welcome_message":
        await edit_welcome_message(update, context)
    elif data == "edit_welcome_video":
        await edit_welcome_video(update, context)
    elif data == "edit_backup_group_link":
        await edit_backup_group_link(update, context)
    elif data == "show_stats":
        await show_stats(update, context)
    elif data == "back_to_main":
        await menu(update, context)

# ===============================
# ERROR HANDLER
# ===============================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors and log them."""
    print(f"Update {update} caused error {context.error}")
    traceback.print_exc()

# ===============================
# MAIN
# ===============================
def main():
    """Initialize and run the bot."""
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.ALL & filters.Chat(ADMIN_CHAT_ID) & ~filters.REPLY, admin_input))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.Chat(ADMIN_CHAT_ID), forward_to_admin))
    app.add_handler(MessageHandler(filters.ALL & filters.Chat(ADMIN_CHAT_ID) & filters.REPLY, reply_from_admin))
    app.add_error_handler(error_handler)
    print("✅ Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()