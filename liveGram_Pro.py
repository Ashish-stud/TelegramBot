import os
import traceback
import re
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
TOKEN = "8292810744:AAGTYsSiIU_cnRRNjG2JIKznxowTt7_x4Ds"  # Replace with your real bot token
ADMIN_CHAT_ID = 7350047143
VIDEO_FILE = "circle.mp4"
WELCOME_MESSAGE = "🎉 Welcome {mention}, Aap Yahaan Padhaare! 😊"
ENTRY_WELCOME_MESSAGE = "🎉 Welcome {mention} to the group! Enjoy your stay! 😊"

# Persistent storage for users and config
users = set()  # Active users
blocked_users = set()  # Blocked users
config = {
    "welcome_message": WELCOME_MESSAGE,
    "entry_welcome_message": ENTRY_WELCOME_MESSAGE,
    "video_file": VIDEO_FILE,
    "welcome_buttons": [
        {"text": "✨ Visit Backup Group", "url": "https://t.me/+m1urakBVenAzOWQx"},
        {"text": "📩 Contact Admin", "url": f"tg://user?id={ADMIN_CHAT_ID}"}
    ]
}

# ===============================
# UTILITY FUNCTIONS
# ===============================
async def delete_previous_messages(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Delete previous bot messages in the chat."""
    if chat_id in context.user_data and 'bot_messages' in context.user_data[chat_id]:
        for msg_id in context.user_data[chat_id]['bot_messages'][:]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except (BadRequest, Forbidden, TelegramError) as e:
                print(f"Failed to delete message {msg_id} in chat {chat_id}: {e}")
        context.user_data[chat_id]['bot_messages'] = []

def initialize_user_data(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Initialize user data if not present."""
    if chat_id not in context.user_data:
        context.user_data[chat_id] = {'bot_messages': []}

# ===============================
# WELCOME HANDLERS
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command and send welcome message and video."""
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        users.add(chat_id)
        blocked_users.discard(chat_id)
        initialize_user_data(chat_id, context)

        mention = f"@{user.username}" if user.username else user.first_name
        keyboard = []
        for button in config["welcome_buttons"]:
            text = button["text"]
            url = button["url"]
            if not url.startswith(('http://', 'https://', 'tg://')):
                print(f"Invalid URL in config: {url}")
                continue
            keyboard.append([InlineKeyboardButton(text, url=url)])

        try:
            welcome_msg = await update.message.reply_text(
                config["welcome_message"].format(mention=mention, user_first_name=user.first_name),
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            context.user_data[chat_id]['bot_messages'].append(welcome_msg.message_id)
        except Forbidden:
            print(f"User {chat_id} has blocked the bot.")
            users.discard(chat_id)
            blocked_users.add(chat_id)
            return
        except TelegramError as e:
            print(f"Failed to send welcome message to {chat_id}: {e}")
            return

        if config["video_file"] and os.path.exists(config["video_file"]):
            video_path = config["video_file"]
            file_size = os.path.getsize(video_path)
            use_video_note = file_size <= 1_000_000  # 1 MB limit for video notes
            if not use_video_note:
                print(f"Video file '{video_path}' too large for video note: {file_size} bytes. Using send_video.")
                if chat_id == ADMIN_CHAT_ID:
                    try:
                        await context.bot.send_message(
                            ADMIN_CHAT_ID,
                            f"⚠️ Video '{video_path}' is too large ({file_size / 1_000_000:.2f} MB) for video note. Using regular video. Please upload a video <1 MB for video notes."
                        )
                    except TelegramError:
                        pass
            try:
                with open(video_path, "rb") as video:
                    if use_video_note:
                        video_msg = await context.bot.send_video_note(
                            chat_id,
                            video,
                            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                        )
                    else:
                        video_msg = await context.bot.send_video(
                            chat_id,
                            video,
                            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                        )
                    context.user_data[chat_id]['bot_messages'].append(video_msg.message_id)
            except (Forbidden, TelegramError) as e:
                print(f"Failed to send video{' note' if use_video_note else ''} to {chat_id}: {e}")
                if chat_id == ADMIN_CHAT_ID:
                    try:
                        await context.bot.send_message(
                            ADMIN_CHAT_ID,
                            f"⚠️ Failed to send welcome video: {e}. Check '{video_path}'."
                        )
                    except TelegramError:
                        pass
        elif chat_id == ADMIN_CHAT_ID and config["video_file"]:
            try:
                await context.bot.send_message(
                    ADMIN_CHAT_ID,
                    f"⚠️ Welcome video '{config['video_file']}' not found."
                )
            except TelegramError:
                pass
    except Exception as e:
        print(f"Unexpected error in start: {e}")
        traceback.print_exc()

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new group members and send entry welcome message."""
    try:
        chat_id = update.effective_chat.id
        for user in update.message.new_chat_members:
            users.add(user.id)
            blocked_users.discard(user.id)
            initialize_user_data(user.id, context)
            mention = f"@{user.username}" if user.username else user.first_name
            keyboard = []
            for button in config["welcome_buttons"]:
                text = button["text"]
                url = button["url"]
                if not url.startswith(('http://', 'https://', 'tg://')):
                    print(f"Invalid URL in config: {url}")
                    continue
                keyboard.append([InlineKeyboardButton(text, url=url)])

            try:
                welcome_msg = await context.bot.send_message(
                    chat_id,
                    config["entry_welcome_message"].format(mention=mention, user_first_name=user.first_name),
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
                context.user_data[user.id]['bot_messages'].append(welcome_msg.message_id)
            except Forbidden:
                print(f"User {user.id} has blocked the bot or chat {chat_id} restricts messages.")
                users.discard(user.id)
                blocked_users.add(user.id)
            except TelegramError as e:
                print(f"Failed to send entry welcome message to {user.id} in chat {chat_id}: {e}")

            if config["video_file"] and os.path.exists(config["video_file"]):
                video_path = config["video_file"]
                file_size = os.path.getsize(video_path)
                use_video_note = file_size <= 1_000_000
                if not use_video_note:
                    print(f"Video file '{video_path}' too large for video note: {file_size} bytes. Using send_video.")
                    if chat_id == ADMIN_CHAT_ID:
                        try:
                            await context.bot.send_message(
                                ADMIN_CHAT_ID,
                                f"⚠️ Video '{video_path}' is too large ({file_size / 1_000_000:.2f} MB) for video note. Using regular video. Please upload a video <1 MB for video notes."
                            )
                        except TelegramError:
                            pass
                try:
                    with open(video_path, "rb") as video:
                        if use_video_note:
                            video_msg = await context.bot.send_video_note(
                                chat_id,
                                video,
                                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                            )
                        else:
                            video_msg = await context.bot.send_video(
                                chat_id,
                                video,
                                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                            )
                        context.user_data[user.id]['bot_messages'].append(video_msg.message_id)
                except (Forbidden, TelegramError) as e:
                    print(f"Failed to send video{' note' if use_video_note else ''} to {chat_id}: {e}")
                    if chat_id == ADMIN_CHAT_ID:
                        try:
                            await context.bot.send_message(
                                ADMIN_CHAT_ID,
                                f"⚠️ Failed to send entry welcome video: {e}. Check '{video_path}'."
                            )
                        except TelegramError:
                            pass
            elif chat_id == ADMIN_CHAT_ID and config["video_file"]:
                try:
                    await context.bot.send_message(
                        ADMIN_CHAT_ID,
                        f"⚠️ Welcome video '{config['video_file']}' not found."
                    )
                except TelegramError:
                    pass
    except Exception as e:
        print(f"Unexpected error in new_chat_members: {e}")
        traceback.print_exc()

# ===============================
# STATS COMMAND
# ===============================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display detailed bot statistics for admin."""
    try:
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("🚫 Only admins can use this command.")
            return
        initialize_user_data(update.effective_chat.id, context)
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
            f"🚫 Blocked Users List:\n{blocked_list}"
        )
        msg = await update.message.reply_text(stats_message)
        context.user_data[update.effective_chat.id]['bot_messages'].append(msg.message_id)
    except TelegramError as e:
        print(f"Failed to send stats message: {e}")
    except Exception as e:
        print(f"Unexpected error in stats: {e}")
        traceback.print_exc()

# ===============================
# ADMIN MENU
# ===============================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin menu with broadcast and config options."""
    try:
        if update.effective_chat.id != ADMIN_CHAT_ID:
            return
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)

        keyboard = [
            [InlineKeyboardButton("📢 Broadcast Options", callback_data="broadcast_menu")],
            [InlineKeyboardButton("🛠️ Welcome Configuration", callback_data="welcome_config_menu")],
            [InlineKeyboardButton("📊 Show Stats", callback_data="show_stats")]
        ]
        menu_text = "⚙️ Admin Menu: Select an option"
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                msg = await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard))
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit menu message: {e}")
            msg = await context.bot.send_message(chat_id, menu_text, reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in menu: {e}")
        traceback.print_exc()

# --- Welcome Config Menu ---
async def welcome_config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display welcome configuration submenu."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)

        keyboard = [
            [InlineKeyboardButton("📝 Edit Post-Entry Welcome", callback_data="edit_welcome_message")],
            [InlineKeyboardButton("📝 Edit Group Entry Welcome", callback_data="edit_entry_welcome_message")],
            [InlineKeyboardButton("🎞️ Edit Welcome Video", callback_data="edit_welcome_video")],
            [InlineKeyboardButton("🔗 Edit Welcome Buttons", callback_data="edit_welcome_buttons")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]
        ]
        try:
            if q:
                await q.edit_message_text("🛠️ Welcome Configuration: Select an option", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                msg = await context.bot.send_message(chat_id, "🛠️ Welcome Configuration: Select an option", reply_markup=InlineKeyboardMarkup(keyboard))
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit welcome config menu: {e}")
            msg = await context.bot.send_message(chat_id, "🛠️ Welcome Configuration: Select an option", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in welcome_config_menu: {e}")
        traceback.print_exc()

# --- Broadcast Menu ---
async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display broadcast options submenu."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)

        keyboard = [
            [InlineKeyboardButton("📝 Add Text", callback_data="add_text")],
            [InlineKeyboardButton("📸 Add Photo", callback_data="add_photo")],
            [InlineKeyboardButton("🎥 Add Video", callback_data="add_video")],
            [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
            [InlineKeyboardButton("✅ Publish", callback_data="publish"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]
        ]
        try:
            if q:
                await q.edit_message_text("📢 Broadcast Options: Prepare your message", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                msg = await context.bot.send_message(chat_id, "📢 Broadcast Options: Prepare your message", reply_markup=InlineKeyboardMarkup(keyboard))
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit broadcast menu: {e}")
            msg = await context.bot.send_message(chat_id, "📢 Broadcast Options: Prepare your message", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in broadcast_menu: {e}")
        traceback.print_exc()

# ===============================
# BROADCAST HANDLERS
# ===============================
async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add text for broadcast."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "text"
        try:
            msg = await (q.edit_message_text("✍️ Send the broadcast text.") if q else update.message.reply_text("✍️ Send the broadcast text."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit add text prompt: {e}")
            msg = await context.bot.send_message(chat_id, "✍️ Send the broadcast text.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in add_text: {e}")
        traceback.print_exc()

async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a photo for broadcast."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "photo"
        try:
            msg = await (q.edit_message_text("📸 Send the broadcast photo.") if q else update.message.reply_text("📸 Send the broadcast photo."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit add photo prompt: {e}")
            msg = await context.bot.send_message(chat_id, "📸 Send the broadcast photo.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in add_photo: {e}")
        traceback.print_exc()

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a video for broadcast."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "video"
        try:
            msg = await (q.edit_message_text("🎥 Send the broadcast video.") if q else update.message.reply_text("🎥 Send the broadcast video."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit add video prompt: {e}")
            msg = await context.bot.send_message(chat_id, "🎥 Send the broadcast video.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in add_video: {e}")
        traceback.print_exc()

async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a button for broadcast."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "button"
        try:
            msg = await (q.edit_message_text("➕ Send button in format: Text|https://link or (Text)- Tap To Share -share:link") if q else update.message.reply_text("➕ Send button in format: Text|https://link or (Text)- Tap To Share -share:link"))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit add button prompt: {e}")
            msg = await context.bot.send_message(chat_id, "➕ Send button in format: Text|https://link or (Text)- Tap To Share -share:link")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in add_button: {e}")
        traceback.print_exc()

async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all subscribed users."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)

        text = context.user_data.get('text')
        photo = context.user_data.get('photo')
        video = context.user_data.get('video')
        buttons = context.user_data.get('buttons', [])
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(t, url=u)] for t, u in buttons if u.startswith(('http://', 'https://', 'tg://'))]) if buttons else None

        recipients = users - {ADMIN_CHAT_ID}
        failed = 0
        for uid in recipients:
            initialize_user_data(uid, context)
            try:
                if video:
                    msg = await context.bot.send_video(uid, video, caption=text or "", reply_markup=markup)
                elif photo:
                    msg = await context.bot.send_photo(uid, photo, caption=text or "", reply_markup=markup)
                elif text:
                    msg = await context.bot.send_message(uid, text, reply_markup=markup)
                context.user_data[uid]['bot_messages'].append(msg.message_id)
            except Forbidden:
                print(f"User {uid} has blocked the bot.")
                users.discard(uid)
                blocked_users.add(uid)
                failed += 1
            except TelegramError as e:
                print(f"Failed to send broadcast to {uid}: {e}")
                failed += 1

        try:
            msg = await (q.edit_message_text(f"✅ Broadcast sent to {len(recipients) - failed}/{len(recipients)} users") if q else context.bot.send_message(chat_id, f"✅ Broadcast sent to {len(recipients) - failed}/{len(recipients)} users"))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit publish confirmation: {e}")
            msg = await context.bot.send_message(chat_id, f"✅ Broadcast sent to {len(recipients) - failed}/{len(recipients)} users")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        context.user_data.clear()
    except Exception as e:
        print(f"Unexpected error in publish: {e}")
        traceback.print_exc()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current broadcast operation."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data.clear()
        try:
            msg = await (q.edit_message_text("❌ Broadcast cancelled.") if q else context.bot.send_message(chat_id, "❌ Broadcast cancelled."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit cancel confirmation: {e}")
            msg = await context.bot.send_message(chat_id, "❌ Broadcast cancelled.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in cancel: {e}")
        traceback.print_exc()

# ===============================
# WELCOME CONFIGURATION
# ===============================
async def edit_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of post-entry welcome message."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "welcome_message"
        try:
            msg = await (q.edit_message_text("✍️ Send the new post-entry welcome message. Use {mention} for username, {user_first_name} for first name.") if q else update.message.reply_text("✍️ Send the new post-entry welcome message. Use {mention} for username, {user_first_name} for first name."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit welcome message prompt: {e}")
            msg = await context.bot.send_message(chat_id, "✍️ Send the new post-entry welcome message. Use {mention} for username, {user_first_name} for first name.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in edit_welcome_message: {e}")
        traceback.print_exc()

async def edit_entry_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of group entry welcome message."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "entry_welcome_message"
        try:
            msg = await (q.edit_message_text("✍️ Send the new group entry welcome message. Use {mention} for username, {user_first_name} for first name.") if q else update.message.reply_text("✍️ Send the new group entry welcome message. Use {mention} for username, {user_first_name} for first name."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit entry welcome message prompt: {e}")
            msg = await context.bot.send_message(chat_id, "✍️ Send the new group entry welcome message. Use {mention} for username, {user_first_name} for first name.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in edit_entry_welcome_message: {e}")
        traceback.print_exc()

async def edit_welcome_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of welcome video."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "welcome_video"
        try:
            msg = await (q.edit_message_text("🎞️ Send a new welcome video file (<1 MB for video note) or type 'remove' to clear.") if q else update.message.reply_text("🎞️ Send a new welcome video file (<1 MB for video note) or type 'remove' to clear."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit welcome video prompt: {e}")
            msg = await context.bot.send_message(chat_id, "🎞️ Send a new welcome video file (<1 MB for video note) or type 'remove' to clear.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in edit_welcome_video: {e}")
        traceback.print_exc()

async def edit_welcome_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing of welcome buttons."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        context.user_data['awaiting'] = "welcome_buttons"
        context.user_data['temp_buttons'] = []
        try:
            msg = await (q.edit_message_text("🔗 Send a button in format: Text[https://link] or (Text)- Tap To Share -share:link. Send 'done' to save or 'clear' to remove all.") if q else update.message.reply_text("🔗 Send a button in format: Text[https://link] or (Text)- Tap To Share -share:link. Send 'done' to save or 'clear' to remove all."))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit welcome buttons prompt: {e}")
            msg = await context.bot.send_message(chat_id, "🔗 Send a button in format: Text[https://link] or (Text)- Tap To Share -share:link. Send 'done' to save or 'clear' to remove all.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in edit_welcome_buttons: {e}")
        traceback.print_exc()

async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin inputs for broadcast, welcome, and buttons."""
    try:
        if update.effective_chat.id != ADMIN_CHAT_ID:
            return
        if update.message.reply_to_message:
            return

        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        awaiting = context.user_data.get('awaiting')
        if not awaiting:
            return

        success = False
        text_input = update.message.text if update.message.text else None

        if awaiting == "text" and text_input:
            context.user_data['text'] = text_input
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
        elif awaiting == "button" and text_input:
            share_match = re.match(r"^\((.*?)\)- Tap To Share -share:(.+)$", text_input.strip())
            if share_match:
                text, link = share_match.groups()
                url = f"tg://msg_url?url={link.strip()}"
                if 'buttons' not in context.user_data:
                    context.user_data['buttons'] = []
                context.user_data['buttons'].append((text.strip(), url))
                msg = await update.message.reply_text(f"✅ Share button [{text.strip()}] added.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                success = True
            else:
                try:
                    text, url = text_input.split("|", 1)
                    if not url.startswith(('http://', 'https://', 'tg://')):
                        msg = await update.message.reply_text("⚠️ Invalid URL. Use http://, https://, or tg:// links.")
                        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                        return
                    if 'buttons' not in context.user_data:
                        context.user_data['buttons'] = []
                    context.user_data['buttons'].append((text.strip(), url.strip()))
                    msg = await update.message.reply_text(f"✅ Button [{text.strip()}] added.")
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                    success = True
                except ValueError:
                    msg = await update.message.reply_text("⚠️ Invalid format. Use: Text|https://link or (Text)- Tap To Share -share:link")
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        elif awaiting == "welcome_message" and text_input:
            config['welcome_message'] = text_input
            msg = await update.message.reply_text("✅ Post-entry welcome message updated.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        elif awaiting == "entry_welcome_message" and text_input:
            config['entry_welcome_message'] = text_input
            msg = await update.message.reply_text("✅ Group entry welcome message updated.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            success = True
        elif awaiting == "welcome_video":
            if text_input and text_input.lower().strip() == "remove":
                config['video_file'] = ""
                msg = await update.message.reply_text("✅ Welcome video removed.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                success = True
            elif update.message.video:
                file = await update.message.video.get_file()
                file_path = f"welcome_video_{update.message.video.file_id}.mp4"
                await file.download_to_drive(file_path)
                file_size = os.path.getsize(file_path)
                if file_size > 1_000_000:
                    msg = await update.message.reply_text(
                        f"⚠️ Video is too large ({file_size / 1_000_000:.2f} MB) for video note. Saved, but please upload a video <1 MB for video notes."
                    )
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                config['video_file'] = file_path
                msg = await update.message.reply_text("✅ Welcome video updated.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                success = True
            else:
                msg = await update.message.reply_text("⚠️ Please send a video file or type 'remove'.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        elif awaiting == "welcome_buttons" and text_input:
            text = text_input.strip()
            if text.lower() == "done":
                if context.user_data.get('temp_buttons'):
                    config['welcome_buttons'] = context.user_data['temp_buttons']
                    msg = await update.message.reply_text(f"✅ Welcome buttons updated. Total: {len(config['welcome_buttons'])}")
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                    success = True
                else:
                    msg = await update.message.reply_text("⚠️ No buttons added. Type 'clear' to remove all or add buttons first.")
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            elif text.lower() == "clear":
                config['welcome_buttons'] = []
                context.user_data['temp_buttons'] = []
                msg = await update.message.reply_text("✅ All welcome buttons removed.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                success = True
            else:
                share_match = re.match(r"^\((.*?)\)- Tap To Share -share:(.+)$", text)
                if share_match:
                    button_text, link = share_match.groups()
                    url = f"tg://msg_url?url={link.strip()}"
                    if not context.user_data.get('temp_buttons'):
                        context.user_data['temp_buttons'] = []
                    context.user_data['temp_buttons'].append({"text": button_text.strip(), "url": url})
                    msg = await update.message.reply_text(f"✅ Share button [{button_text.strip()}] added. Send another or type 'done'/'clear'.")
                    context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                    success = True
                else:
                    try:
                        button_text, url = text.split("[", 1)
                        url = url.rstrip("]").strip()
                        if not url.startswith(('http://', 'https://', 'tg://')):
                            msg = await update.message.reply_text("⚠️ Invalid URL. Use http://, https://, or tg:// links.")
                            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                            return
                        if not context.user_data.get('temp_buttons'):
                            context.user_data['temp_buttons'] = []
                        context.user_data['temp_buttons'].append({"text": button_text.strip(), "url": url})
                        msg = await update.message.reply_text(f"✅ Button [{button_text.strip()}] added. Send another or type 'done'/'clear'.")
                        context.user_data[chat_id]['bot_messages'].append(msg.message_id)
                        success = True
                    except ValueError:
                        msg = await update.message.reply_text("⚠️ Invalid format. Use: Text[https://link] or (Text)- Tap To Share -share:link")
                        context.user_data[chat_id]['bot_messages'].append(msg.message_id)

        if success:
            context.user_data['awaiting'] = None if awaiting not in ["welcome_buttons"] else "welcome_buttons"
            if awaiting in ["text", "photo", "video", "button"]:
                await broadcast_menu(update, context)
            elif awaiting in ["welcome_message", "entry_welcome_message", "welcome_video"] or (awaiting == "welcome_buttons" and text_input and text_input.lower() in ["done", "clear"]):
                await welcome_config_menu(update, context)
            else:
                await menu(update, context)
    except Exception as e:
        print(f"Unexpected error in admin_input: {e}")
        traceback.print_exc()
        try:
            msg = await update.message.reply_text("⚠️ An error occurred. Please try again.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except TelegramError as e2:
            print(f"Failed to send error message in admin_input: {e2}")

# ===============================
# USER → ADMIN FORWARD / ADMIN REPLY
# ===============================
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user messages to admin and provide feedback."""
    try:
        if update.effective_chat.id == ADMIN_CHAT_ID:
            return
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)
        if update.message.text and update.message.text.lower().strip() == "hello":
            try:
                hello_msg = await update.message.reply_text("Hello! How can I assist you? 😊")
                context.user_data[chat_id]['bot_messages'].append(hello_msg.message_id)
            except Forbidden:
                print(f"User {chat_id} has blocked the bot.")
                users.discard(chat_id)
                blocked_users.add(chat_id)
            except TelegramError as e:
                print(f"Failed to send hello response to {chat_id}: {e}")
            return

        try:
            await update.message.forward(ADMIN_CHAT_ID)
            feedback_msg = await update.message.reply_text("📬 Message sent to admin.")
            context.user_data[chat_id]['bot_messages'].append(feedback_msg.message_id)
        except Forbidden:
            print(f"User {chat_id} has blocked the bot.")
            users.discard(chat_id)
            blocked_users.add(chat_id)
        except TelegramError as e:
            print(f"Failed to forward message from {chat_id}: {e}")
            try:
                feedback_msg = await update.message.reply_text("⚠️ Failed to send your message. Please try again.")
                context.user_data[chat_id]['bot_messages'].append(feedback_msg.message_id)
            except TelegramError as e2:
                print(f"Failed to send forward error message: {e2}")
    except Exception as e:
        print(f"Unexpected error in forward_to_admin: {e}")
        traceback.print_exc()

async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin replies to users."""
    try:
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
        initialize_user_data(target_id, context)
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
            context.user_data[target_id]['bot_messages'].append(reply_msg.message_id)
        except Forbidden:
            print(f"User {target_id} has blocked the bot.")
            users.discard(target_id)
            blocked_users.add(target_id)
            await update.message.reply_text("⚠️ The user has blocked the bot.")
        except TelegramError as e:
            print(f"Failed to send reply to {target_id}: {e}")
            await update.message.reply_text(f"⚠️ Failed to send reply: {e}")
    except Exception as e:
        print(f"Unexpected error in reply_from_admin: {e}")
        traceback.print_exc()

# ===============================
# STATS HANDLER
# ===============================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display stats via menu callback."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        chat_id = update.effective_chat.id
        await delete_previous_messages(chat_id, context)
        initialize_user_data(chat_id, context)

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
            f"🚫 Blocked Users List:\n{blocked_list}"
        )
        try:
            msg = await (q.edit_message_text(stats_message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]])) if q else context.bot.send_message(chat_id, stats_message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]])))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except BadRequest as e:
            print(f"Failed to edit stats message: {e}")
            msg = await context.bot.send_message(chat_id, stats_message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main")]]))
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
    except Exception as e:
        print(f"Unexpected error in show_stats: {e}")
        traceback.print_exc()

# ===============================
# BROADCAST CALLBACK HANDLER
# ===============================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers."""
    try:
        q = update.callback_query
        if q:
            await q.answer()
        data = q.data

        if data == "broadcast_menu":
            await broadcast_menu(update, context)
        elif data == "welcome_config_menu":
            await welcome_config_menu(update, context)
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
        elif data == "edit_entry_welcome_message":
            await edit_entry_welcome_message(update, context)
        elif data == "edit_welcome_video":
            await edit_welcome_video(update, context)
        elif data == "edit_welcome_buttons":
            await edit_welcome_buttons(update, context)
        elif data == "show_stats":
            await show_stats(update, context)
        elif data == "back_to_main":
            await menu(update, context)
    except Exception as e:
        print(f"Unexpected error in admin_callback: {e}")
        traceback.print_exc()
        chat_id = update.effective_chat.id
        initialize_user_data(chat_id, context)
        try:
            msg = await context.bot.send_message(chat_id, "⚠️ An error occurred. Please try again.")
            context.user_data[chat_id]['bot_messages'].append(msg.message_id)
        except TelegramError as e2:
            print(f"Failed to send callback error message: {e2}")

# ===============================
# ERROR HANDLER
# ===============================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors and log them."""
    try:
        print(f"Update {update} caused error {context.error}")
        traceback.print_exc()
        if update and update.effective_chat:
            chat_id = update.effective_chat.id
            initialize_user_data(chat_id, context)
            try:
                msg = await context.bot.send_message(chat_id, "⚠️ An unexpected error occurred. Please try again.")
                context.user_data[chat_id]['bot_messages'].append(msg.message_id)
            except TelegramError as e:
                print(f"Failed to send error handler message: {e}")
    except Exception as e:
        print(f"Unexpected error in error_handler: {e}")
        traceback.print_exc()

# ===============================
# MAIN
# ===============================
def main():
    """Initialize and run the bot."""
    try:
        app = ApplicationBuilder().token(TOKEN).read_timeout(20).write_timeout(20).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("menu", menu))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CallbackQueryHandler(admin_callback))
        app.add_handler(MessageHandler(filters.ALL & filters.Chat(ADMIN_CHAT_ID) & ~filters.REPLY, admin_input))
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.Chat(ADMIN_CHAT_ID), forward_to_admin))
        app.add_handler(MessageHandler(filters.ALL & filters.Chat(ADMIN_CHAT_ID) & filters.REPLY, reply_from_admin))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
        app.add_error_handler(error_handler)
        print("✅ Bot running...")
        app.run_polling()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
