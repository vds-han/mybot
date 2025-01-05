# bot.py

import time
import os
import logging
import qrcode
import io
import json
import threading
import queue
import uuid
from datetime import datetime
from pytz import timezone, utc
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ParseMode, InputMediaPhoto
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)
from telegram.error import BadRequest
from flask import Flask, request, abort
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from database import (
    init_db, SessionLocal, User, Reward, Transaction,
    Redemption, Event, UserSession, Configuration, TNGPin
)

from models import SensitiveInfoFilter

# Load environment variables from .env file
load_dotenv()

# Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # e.g., "YourBotUsername"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your Render app's public URL, e.g., "https://your-app-name.onrender.com"
PORT = int(os.getenv("PORT", 8443))  # Render sets the PORT environment variable automatically

MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "rubbish/disposal")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")  # For error notifications

# Ensure critical environment variables are defined
if not TOKEN:
    raise ValueError("Environment variable TELEGRAM_BOT_TOKEN is not set.")
if not WEBHOOK_URL:
    raise ValueError("Environment variable WEBHOOK_URL is not set.")

# Image URLs
COMPANY_IMAGE_URL = "https://img.freepik.com/premium-photo/earth-day-poster-background-illustration-vertical-concept-design-poster-greeting-card-flat-lay_108611-3386.jpg"  # Main menu image
CHECK_BALANCE_IMAGE_URL = "https://i.pinimg.com/originals/9f/ba/ad/9fbaad5f595b5099c1950d211de4892b.jpg"
VIEW_EVENTS_IMAGE_URL = "https://i.pinimg.com/originals/c3/b7/30/c3b73071bac1d682526046adbcbf5777.jpg"
REDEEM_REWARDS_IMAGE_URL = "https://static.vecteezy.com/system/resources/previews/000/299/799/original/earth-day-vector-design-for-card-poster-banner-flyer.jpg"
LEADERBOARD_IMAGE_URL = "https://th.bing.com/th/id/OIP.AytYm-aNAOHKnfBk_4UxiwHaHa?rs=1&pid=ImgDetMain"
VIEW_DISPOSAL_HISTORY_IMAGE_URL = "https://i.pinimg.com/originals/ae/b3/20/aeb32056367d7927dc69888bc4398d68.jpg"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)  # Define logger here

# Apply sensitive info filter
sensitive_filter = SensitiveInfoFilter([TOKEN, os.getenv("DATABASE_URL"), os.getenv("API_KEY")])

# Add the filter to all handlers
for handler in logging.getLogger().handlers:
    handler.addFilter(sensitive_filter)

# Enable logging for MQTT
mqtt.Client().enable_logger(logger)

# Create a Flask app
app = Flask(__name__)

# Initialize the message queue
message_queue = queue.Queue()

# Initialize the Updater and Dispatcher globally
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

@app.route("/")
def home():
    return "Bot is running!"

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), updater.bot)
        dispatcher.process_update(update)
        return "OK", 200
    else:
        abort(403)

# Utility Functions
def generate_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def main_menu():
    """Main menu inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
        [InlineKeyboardButton("🎁 Redeem Rewards", callback_data="redeem_rewards")],
        [InlineKeyboardButton("📅 View Events", callback_data="view_events")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🗑️ View Disposal History", callback_data="view_disposal_history")],  # New button
    ]
    return InlineKeyboardMarkup(keyboard)

def safe_edit_message_media(query, media_url, caption, reply_markup=None):
    """Safely edit the message media (photo) and caption."""
    try:
        # Add cache busting to the media URL
        cache_busted_url = f"{media_url}?v={int(time.time())}"

        media = InputMediaPhoto(media=cache_busted_url, caption=caption, parse_mode=ParseMode.MARKDOWN)
        query.edit_message_media(
            media=media,
            reply_markup=reply_markup if reply_markup else main_menu()
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            logger.error(f"BadRequest in safe_edit_message_media: {e}")
            raise e
    except Exception as e:
        logger.error(f"Unexpected error in safe_edit_message_media: {e}")
        raise e

def delete_current_event_poster(context: CallbackContext, chat_id: int):
    """Delete the current event poster if it exists."""
    current_photo_message = context.user_data.get('current_event_photo')
    if current_photo_message:
        try:
            context.bot.delete_message(
                chat_id=chat_id,
                message_id=current_photo_message
            )
            logger.info(f"Deleted event poster message ID: {current_photo_message}")
        except BadRequest as e:
            logger.error(f"BadRequest error deleting event poster message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting event poster message: {e}")
        finally:
            context.user_data.pop('current_event_photo', None)

def send_main_menu(chat_id, context, text="What would you like to do?"):
    cache_busted_url = f"{COMPANY_IMAGE_URL}?v={int(time.time())}"  # Add a unique query string to prevent caching

    context.bot.send_photo(
        chat_id=chat_id,
        photo=cache_busted_url,
        caption=text,
        reply_markup=main_menu()
    )

def send_notification_message(bot, chat_id: int, text: str):
    """Send a notification message to the user."""
    try:
        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to send notification to chat ID {chat_id}: {e}")

def request_registration(update: Update, context: CallbackContext):
    """Send a message requesting the user's phone number."""
    phone_button = KeyboardButton("📞 Share Phone Number", request_contact=True)
    reply_markup = ReplyKeyboardMarkup(
        [[phone_button]], one_time_keyboard=True, resize_keyboard=True
    )
    update.message.reply_text(
        "📱 Please share your phone number to register:",
        reply_markup=reply_markup,
    )

def start(update: Update, context: CallbackContext):
    """Handle the /start command with optional activation parameter."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args  # List of arguments passed with /start

    logger.info(f"Received /start command from user: {user_id}, arguments: {args}")

    # Initialize the database session
    db = SessionLocal()

    try:
        # Check if the user is already registered
        user = db.query(User).filter_by(telegram_id=user_id).first()
        config = db.query(Configuration).first()

        if user:
            # If the user exists, handle the optional "activate_bin" parameter
            if args and args[0] == "activate_bin":
                logger.info(f"Attempting to activate user: {user.name} (ID: {user.telegram_id})")

                # Deactivate the previous active user (if any)
                if config and config.active_user_id:
                    if config.active_user_id != user.id:
                        previous_user = db.query(User).filter_by(id=config.active_user_id).first()
                        if previous_user:
                            logger.info(f"Deactivating previous user: {previous_user.name} (ID: {previous_user.telegram_id}).")
                            # Optionally, notify the previous user about deactivation
                            try:
                                context.bot.send_message(
                                    chat_id=previous_user.telegram_id,
                                    text="🔔 You have been deactivated as the active user for the bin."
                                )
                            except Exception as e:
                                logger.warning(f"Unable to notify previous user: {e}")

                # Ensure only one Configuration row exists
                if not config:
                    config = Configuration(active_user_id=user.id)
                    db.add(config)
                    logger.info(f"Created new Configuration with active_user_id: {user.id}")
                else:
                    config.active_user_id = user.id
                    logger.info(f"Set active_user_id to: {user.id}")

                db.commit()

                # Notify the user
                update.message.reply_text(
                    f"🎉 Welcome, {user.name}! You are now the active user for the bin.\n"
                    f"Start disposing to earn points."
                )
                logger.info(f"User {user.name} (ID: {user.telegram_id}) is now active.")
            else:
                # Regular /start command without activation
                send_main_menu(chat_id, context, text=f"Hello {user.name}! Welcome back.")
        else:
            # If the user is new
            if args and args[0] == "activate_bin":
                # User scanned the QR code but is not registered
                update.message.reply_text(
                    "🚫 You need to register first. Please share your phone number to register."
                )
                request_registration(update, context)
                logger.info(f"User {user_id} attempted activation without registration.")
            else:
                # Regular /start command for a new user
                update.message.reply_text(
                    "👋 Welcome! Please register by sharing your phone number to continue."
                )
                request_registration(update, context)
                logger.info(f"New user (ID: {user_id}) prompted to register.")
    except Exception as e:
        logger.error(f"❌ Error processing /start command for user {user_id}: {e}")
        update.message.reply_text("🚫 An error occurred while processing your request. Please try again later.")
    finally:
        db.close()
        logger.info(f"Database session closed for user {user_id}.")

def active_user(update: Update, context: CallbackContext):
    db = SessionLocal()
    config = db.query(Configuration).first()
    if config and config.active_user_id:
        active_user = db.query(User).filter_by(id=config.active_user_id).first()
        if active_user:
            update.message.reply_text(
                f"👤 *Active User:* {active_user.name}\n"
                f"📱 *Telegram ID:* {active_user.telegram_id}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text("⚠️ No active user found.")
    else:
        update.message.reply_text("⚠️ No active user found.")
    db.close()

def register_contact(update: Update, context: CallbackContext):
    """Handle contact sharing and register the user."""
    contact = update.message.contact
    user_id = update.effective_user.id

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=user_id).first()
    if user:
        update.message.reply_text("✅ You are already registered.")
        db.close()
        return

    # Create a new user entry
    user = User(
        telegram_id=user_id,
        phone_number=contact.phone_number,
        name="",  # To be updated
        points=0
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Request the user's name
    context.user_data['registration_step'] = 'awaiting_name'
    update.message.reply_text(
        "📝 Thank you! Please enter your name to complete registration."
    )
    db.close()

def collect_name(update: Update, context: CallbackContext):
    """Handle name input and complete registration."""
    user_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=user_id).first()

    # Validate the registration step
    if not user or 'registration_step' not in context.user_data or context.user_data['registration_step'] != 'awaiting_name':
        update.message.reply_text("❌ Unexpected input. Use /start to register.")
        db.close()
        return

    # Store the name
    user.name = update.message.text.strip()
    db.commit()

    # Inform the user that registration is complete
    update.message.reply_text(
        f"🎉 Thank you, *{user.name}*! Your registration is now complete. Use /start to invoke the bot's main menu.",
        parse_mode=ParseMode.MARKDOWN
    )

    # Clear the registration step
    context.user_data.pop('registration_step', None)
    db.close()

def check_balance_callback(update: Update, context: CallbackContext):
    """Display the user's current balance and update the image."""
    query = update.callback_query
    user_id = query.from_user.id
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=user_id).first()

    if user:
        query.answer()
        message_text = (
            f"👤 *{user.name}*, your current balance is: *{user.points} points*.\n\nWhat would you like to do next?"
        )

        # Delete the current event poster if it exists
        delete_current_event_poster(context, query.message.chat_id)

        # Safely edit the message media with the Check Balance image
        safe_edit_message_media(
            query,
            CHECK_BALANCE_IMAGE_URL,  # Correct image URL
            message_text,             # Correct caption
            reply_markup=main_menu(),
        )
    else:
        query.answer()
        safe_edit_message_media(
            query,
            COMPANY_IMAGE_URL,  # Use an appropriate image URL
            "❌ You are not registered. Please use /start to register.",
            reply_markup=main_menu()
        )
    db.close()

def redeem_rewards_callback(update: Update, context: CallbackContext):
    """Display the rewards menu with appropriate image."""
    query = update.callback_query
    db = SessionLocal()

    # Delete the current event poster if it exists
    delete_current_event_poster(context, query.message.chat_id)

    # Fetch available rewards
    rewards = db.query(Reward).all()
    if rewards:
        message = "🎁 *Available Rewards:*\n\n"
        keyboard = []
        for reward in rewards:
            message += f"{reward.id}. {reward.name} - {reward.points_required} points\n"
            keyboard.append([InlineKeyboardButton(f"{reward.name}", callback_data=f"redeem_{reward.id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
        query.answer()
        
        # Update the message media with the Redeem Rewards image
        safe_edit_message_media(
            query,
            REDEEM_REWARDS_IMAGE_URL,  # Correct image URL
            f"{message}\nSelect a reward to redeem:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query.answer()
        safe_edit_message_media(
            query,
            REDEEM_REWARDS_IMAGE_URL,  # Use appropriate image
            "🛍️ No rewards available at the moment.\n\nWhat would you like to do next?",
            reply_markup=main_menu(),
        )
    db.close()

def get_tng_pin(session: UserSession, reward: Reward, user: User) -> str:
    """
    Retrieves an unused TNG pin for a reward and marks it as used.
    
    Args:
        session (Session): The active database session.
        reward (Reward): The reward object for which the pin is being redeemed.
        user (User): The user redeeming the reward.

    Returns:
        str: The TNG pin if available, or raises an exception if not.
    """
    try:
        # Query the first available unused TNG pin for the specified reward
        tng_pin = session.query(TNGPin).filter(
            TNGPin.reward_id == reward.id,
            TNGPin.used == False
        ).first()

        if not tng_pin:
            raise ValueError(f"No unused TNG pins available for reward: {reward.name}")

        # Mark the pin as used
        tng_pin.used = True
        tng_pin.used_by = user.telegram_id
        tng_pin.used_at = datetime.utcnow()
        logger.info(f"TNG PIN {tng_pin.pin} redeemed by user {user.name} (ID: {user.telegram_id}) at {tng_pin.used_at}")
        
        # Commit the changes to the database
        session.commit()

        return tng_pin.pin
    except Exception as e:
        session.rollback()  # Rollback in case of an error
        raise e
        
def process_reward_selection(update: Update, context: CallbackContext):
    """Process the reward selection and handle redemption."""
    query = update.callback_query
    user_id = query.from_user.id
    db = SessionLocal()

    # Get the reward_id from the callback_data
    data = query.data
    if data.startswith('redeem_'):
        try:
            reward_id = int(data.split('_')[1])
        except (IndexError, ValueError):
            query.answer()
            safe_edit_message_media(
                query,
                COMPANY_IMAGE_URL,  # Use a fallback image URL here
                "❌ Invalid reward selection. Please try again.",
                reply_markup=main_menu()
            )
            db.close()
            return
    else:
        query.answer()
        db.close()
        return

    user = db.query(User).filter_by(telegram_id=user_id).first()

    # Check if user is registered
    if not user:
        query.answer()
        safe_edit_message_media(
            query,
            COMPANY_IMAGE_URL,  # Use a fallback image URL here
            "❌ You are not registered. Please use /start to register.",
            reply_markup=main_menu()
        )
        logger.info(f"{user_id} - Failed redemption: User not registered.")
        db.close()
        return

    reward = db.query(Reward).filter_by(id=reward_id).first()

    if not reward:
        query.answer()
        safe_edit_message_media(
            query,
            COMPANY_IMAGE_URL,  # Use a fallback image URL here
            "❌ Invalid reward selection.",
            reply_markup=main_menu()
        )
        logger.info(f"{user.name} (ID: {user.telegram_id}) - Failed redemption: Invalid reward ID ({reward_id}).")
        db.close()
        return
    if user.points < reward.points_required:
        query.answer()
        safe_edit_message_media(
            query,
            COMPANY_IMAGE_URL,  # Use a fallback image URL here
            "❌ You don't have enough points to redeem this reward.",
            reply_markup=main_menu()
        )
        logger.info(f"{user.name} (ID: {user.telegram_id}) - Failed redemption: Insufficient points.")
        db.close()
        return
    if reward.quantity_available <= 0:
        query.answer()
        safe_edit_message_media(
            query,
            COMPANY_IMAGE_URL,  # Use a fallback image URL here
            "❌ This reward is no longer available.",
            reply_markup=main_menu()
        )
        logger.info(f"{user.name} (ID: {user.telegram_id}) - Failed redemption: Reward out of stock ({reward.name}).")
        db.close()
        return

    # Log redeem attempt
    logger.info(f"{user.name} (ID: {user.telegram_id}) is redeeming {reward.name}")

    # Handle TNG Rewards
    if 'TNG' in reward.name.upper():
        # Attempt to retrieve an available TNG pin
        try:
            tng_pin = get_tng_pin(db, reward, user)
    
            # Deduct points and update reward quantity
            user.points -= reward.points_required
            reward.quantity_available -= 1
    
            # Log the transaction
            transaction = Transaction(
                user_id=user.id,
                points_change=-reward.points_required,
                description=f"Redeemed reward: {reward.name} (PIN: {tng_pin})",
            )
            db.add(transaction)
            db.commit()
    
            # Notify the user
            query.answer()
            safe_edit_message_media(
                query,
                REDEEM_REWARDS_IMAGE_URL,  # Use a valid image URL for success
                f"🎉 *Congratulations*, {user.name}! You've successfully redeemed *{reward.name}*.\n"
                f"🔑 *Your TNG PIN:* {tng_pin}\n"
                f"💰 *Your remaining points:* {user.points}",
                reply_markup=main_menu()
            )
            logger.info(f"{user.name} (ID: {user.telegram_id}) redeemed PIN: {tng_pin}")
        except ValueError as e:
            # Handle case where no TNG PINs are available
            query.answer()
            safe_edit_message_media(
                query,
                REDEEM_REWARDS_IMAGE_URL,  # Use a fallback image
                f"❗️ *Sorry*, no TNG PINs are currently available for *{reward.name}*. Please contact support.",
                reply_markup=main_menu()
            )
            logger.warning(f"No TNG PINs available for {user.name} (ID: {user.telegram_id}) for reward {reward.name}")
    else:
        # Handle non-TNG rewards if applicable
        # Example:
        user.points -= reward.points_required
        reward.quantity_available -= 1
        db.commit()

        # Log the transaction
        transaction = Transaction(
            user_id=user.id,
            points_change=-reward.points_required,
            description=f"Redeemed reward: {reward.name}",
        )
        db.add(transaction)
        db.commit()

        # Send congratulations
        query.answer()
        safe_edit_message_media(
            query,
            REDEEM_REWARDS_IMAGE_URL,  # Use a valid image URL for reward redemption success
            f"🎉 *Congratulations*, {user.name}! You've successfully redeemed *{reward.name}*.\n"
            f"💰 *Your remaining points:* {user.points}",
            reply_markup=main_menu()
        )

        # Log successful redemption
        logger.info(f"{user.name} (ID: {user.telegram_id}) redeemed {reward.name}")
    db.close()

def view_events(update: Update, context: CallbackContext):
    """Display the events menu with buttons and delete the event poster if it exists."""
    query = update.callback_query
    query.answer()
    db = SessionLocal()

    events = db.query(Event).order_by(Event.date).all()
    if events:
        keyboard = []
        for event in events:
            keyboard.append([InlineKeyboardButton(event.name, callback_data=f"event_{event.id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Use safe_edit_message_media
        safe_edit_message_media(
            query,
            VIEW_EVENTS_IMAGE_URL,  
            "📅 *Select an event to view details:*",
            reply_markup=reply_markup
        )
    else:
        query.answer()
        safe_edit_message_media(
            query,
            VIEW_EVENTS_IMAGE_URL,  
            "🛑 No events available at the moment.\n\nWhat would you like to do next?",
            reply_markup=main_menu(),
        )
    db.close()

def event_details(update: Update, context: CallbackContext):
    """Display selected event's details with poster and appropriate image."""
    query = update.callback_query
    query.answer()
    db = SessionLocal()

    # Extract event ID from callback data
    try:
        event_id = int(query.data.split('_')[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Error extracting event ID: {e}")
        safe_edit_message_media(
            query,
            VIEW_EVENTS_IMAGE_URL,  # Use appropriate image URL
            "❌ Invalid event selection. Please try again.",
            reply_markup=main_menu()
        )
        db.close()
        return

    # Query the event from the database
    event = db.query(Event).filter_by(id=event_id).first()
    if event:
        # Prepare the event message
        message = (
            f"📅 *{event.name}*\n"
            f"🗓 *Date:* {event.date.strftime('%Y-%m-%d')}\n"
            f"📝 *Description:* {event.description}"
        )

        # Create reply markup with "Back to Main Menu" button
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ])

        # Check for a valid poster URL
        if event.poster_url:
            try:
                # Update the message media with the Event Poster image
                safe_edit_message_media(
                    query,
                    event.poster_url,  # Correct image URL
                    message,           # Correct caption
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error sending photo for event {event.name}: {e}")
                # Fallback to text-only message if the photo fails
                safe_edit_message_media(
                    query,
                    VIEW_EVENTS_IMAGE_URL,  # Use appropriate fallback image
                    f"{message}\n\n(Unable to load image)",
                    reply_markup=reply_markup
                )
        else:
            # If no poster URL, send text-only message with a default image
            safe_edit_message_media(
                query,
                VIEW_EVENTS_IMAGE_URL,  # Correct image URL
                message,                 # Correct caption
                reply_markup=reply_markup
            )
    else:
        # Event not found
        safe_edit_message_media(
            query,
            VIEW_EVENTS_IMAGE_URL,      # Correct image URL
            "❌ Event not found. Please select a valid event.",
            reply_markup=main_menu()
        )
    db.close()

def view_disposal_history_callback(update: Update, context: CallbackContext):
    """Display the user's disposal history with appropriate image."""
    query = update.callback_query
    user_id = query.from_user.id
    db = SessionLocal()

    # Define your local timezone
    local_tz = timezone("Asia/Kuala_Lumpur")

    user = db.query(User).filter_by(telegram_id=user_id).first()

    if user:
        # Fetch the user's transactions related to disposal
        transactions = (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id, Transaction.description.ilike("%Disposed%"))
            .order_by(Transaction.created_at.desc())
            .limit(10)
            .all()
        )

        if transactions:
            message = "🗑️ *Your Disposal History:*\n\n"
            for transaction in transactions:
                # Convert UTC to local timezone
                utc_time = transaction.created_at.replace(tzinfo=utc)
                local_time = utc_time.astimezone(local_tz)

                # Format the local time properly for display
                message += (
                    f"- {transaction.description.replace('Disposed ', '')} at "
                    f"{local_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
        else:
            message = "📄 *No disposal activity found.*\n\nDispose some rubbish to earn points!"

        query.answer()
        safe_edit_message_media(
            query,
            VIEW_DISPOSAL_HISTORY_IMAGE_URL,  # Correct image URL
            message,                           # Correct caption
            reply_markup=main_menu(),
        )
    else:
        query.answer()
        safe_edit_message_media(
            query,
            VIEW_DISPOSAL_HISTORY_IMAGE_URL,  # Use appropriate image
            "❌ You are not registered. Please use /start to register.",
            reply_markup=main_menu()
        )
    db.close()

def leaderboard_callback(update: Update, context: CallbackContext):
    """Display the leaderboard of users and delete the event poster if it exists."""
    query = update.callback_query
    user_id = query.from_user.id
    db = SessionLocal()

    # Fetch top users by points
    top_users = db.query(User).order_by(User.points.desc()).limit(10).all()

    if top_users:
        message = "🏆 *Leaderboard:*\n\n"
        for idx, user in enumerate(top_users, start=1):
            message += f"{idx}. {user.name} - {user.points} points\n"
        query.answer()

        # Delete the current event poster if it exists
        delete_current_event_poster(context, query.message.chat_id)

        # Update the message media with the Leaderboard image
        safe_edit_message_media(
            query,
            LEADERBOARD_IMAGE_URL,            # Correct image URL
            f"{message}\n\nWhat would you like to do next?",  # Correct caption
            reply_markup=main_menu(),
        )
    else:
        query.answer()

        # Delete the current event poster if it exists
        delete_current_event_poster(context, query.message.chat_id)

        # Update the message media with the Leaderboard image
        safe_edit_message_media(
            query,
            LEADERBOARD_IMAGE_URL,            # Use appropriate image
            "🛑 No users found on the leaderboard.\n\nWhat would you like to do next?",
            reply_markup=main_menu(),
        )
    db.close()

def main_menu_callback(update: Update, context: CallbackContext):
    """Return to the main menu and update the image."""
    query = update.callback_query
    query.answer()
    db = SessionLocal()

    # Delete the current event poster if it exists
    delete_current_event_poster(context, query.message.chat_id)

    # Update the message media with the main menu image
    safe_edit_message_media(
        query,
        COMPANY_IMAGE_URL,             # Correct image URL
        "What would you like to do?",   # Correct caption
        reply_markup=main_menu()
    )
    db.close()

def error_handler(update: object, context: CallbackContext):
    """Handle all errors."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # Notify the administrator
    ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")
    if ADMIN_TELEGRAM_ID:
        try:
            context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=f"⚠️ An error occurred:\n{context.error}"
            )
        except Exception as e:
            logger.warning(f"Unable to notify admin: {e}")
    else:
        logger.warning("Admin Telegram ID not set.")
    
    # Notify the user about the error (optional)
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text(
            "Goats don’t rush, and neither should you—hang tight, we’re almost there!"
        )

# MQTT Client Class

class MQTTClientHandler:
    def __init__(self, broker_url, broker_port, username, password, topic, message_queue):
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic = topic
        self.message_queue = message_queue
        self.client = None
        self.setup_client()  # Call the setup_client method

    def setup_client(self):
        unique_client_id = f"bot_{uuid.uuid4().hex[:8]}"
        logger.info(f"Setting up MQTT client with client ID: {unique_client_id}")
        self.client = mqtt.Client(client_id=unique_client_id)
        # Configure authentication
        if self.username and self.password:
            logger.info("Using MQTT authentication.")
            self.client.username_pw_set(self.username, self.password)

        # Enable TLS if required
        use_tls = os.getenv("MQTT_USE_TLS", "True").lower() == "true"
        if use_tls:
            tls_ca_cert = os.getenv("MQTT_TLS_CA_CERT")
            tls_certfile = os.getenv("MQTT_TLS_CERTFILE")
            tls_keyfile = os.getenv("MQTT_TLS_KEYFILE")

            if tls_ca_cert:
                self.client.tls_set(ca_certs=tls_ca_cert, certfile=tls_certfile, keyfile=tls_keyfile)
                logger.info("🔒 TLS has been configured with provided certificates for MQTT client.")
            else:
                self.client.tls_set()  # Default TLS settings
                logger.info("🔒 TLS has been enabled with default settings for MQTT client.")

            # Optionally, disable certificate verification (not recommended for production)
            tls_insecure = os.getenv("MQTT_TLS_INSECURE", "False").lower() == "true"
            self.client.tls_insecure_set(tls_insecure)

        # Enable logging for MQTT
        self.client.enable_logger(logger)

        # Attach callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_url}:{self.broker_port}...")
            self.client.connect(self.broker_url, self.broker_port, keepalive=60)
            logger.info("🔗 Connected to MQTT Broker!")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT Broker: {e}")
            return

        # Start the MQTT client loop in a separate thread
        threading.Thread(target=self.client.loop_forever, daemon=True).start()
        logger.info("🔄 MQTT client loop started.")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ MQTT Client connected successfully.")
            result, mid = self.client.subscribe(self.topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📡 Successfully subscribed to topic: {self.topic}")
            else:
                logger.error(f"❌ Failed to subscribe to topic: {self.topic}. Error code: {result}")
        else:
            logger.error(f"❌ MQTT Client failed to connect. Return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            payload = msg.payload.decode()
            logger.info(f"📥 Received MQTT message on topic {msg.topic}: {payload}")

            # Parse the JSON payload
            data = json.loads(payload)
            rubbish_type = data.get('rubbish_type')

            if not rubbish_type:
                logger.warning("⚠️ 'rubbish_type' not found in MQTT message.")
                return

            # Assign points based on the rubbish type
            self.assign_points(rubbish_type)

        except json.JSONDecodeError:
            logger.error("❌ Failed to decode MQTT message payload as JSON.")
        except Exception as e:
            logger.error(f"❌ Error in on_message: {e}")

    def assign_points(self, rubbish_type):
        """Assign points to the currently active user for the bin."""
        db = SessionLocal()
        try:
            # Check for an active user
            config = db.query(Configuration).first()
            if not config or not config.active_user_id:
                logger.warning("⚠️ No active user to assign points.")
                return

            active_user = db.query(User).filter_by(id=config.active_user_id).first()
            if not active_user:
                logger.warning("⚠️ Active user does not exist.")
                return

            # Define points per rubbish type
            rubbish_points = {
                "plastic": 10,
                "metal": 25,
                "paper": 5,
                "glass": 15,
            }

            # Get the points for the rubbish type
            points = rubbish_points.get(rubbish_type.lower(), 0)
            if points == 0:
                logger.warning(f"⚠️ Unknown rubbish type received: {rubbish_type}")
                return

            # Generate a timestamp for the disposal (current UTC time)
            disposal_time = datetime.utcnow()

            # Convert disposal_time to local timezone (Malaysia)
            malaysia_tz = timezone("Asia/Kuala_Lumpur")
            local_disposal_time = disposal_time.replace(tzinfo=utc).astimezone(malaysia_tz)

            # Update user points
            active_user.points += points

            # Log the transaction in the database
            transaction = Transaction(
                user_id=active_user.id,
                points_change=points,
                description=f"Disposed {rubbish_type} from the bin",
                created_at=disposal_time
            )
            db.add(transaction)
            db.commit()

            # Log both UTC and local time for clarity
            logger.info(
                f"✅ Assigned {points} points to {active_user.name} for disposing {rubbish_type} "
                f"at {disposal_time} (UTC) / {local_disposal_time} (local time)."
            )

            # Enqueue the notification
            self.message_queue.put({
                'chat_id': active_user.telegram_id,
                'text': (
                    f"🎉 *Great Job*, {active_user.name}!\n\n"
                    f"You've earned *{points} points* for disposing *{rubbish_type}*.\n\n"
                    f"💰 *Your current balance:* {active_user.points} points."
                )
            })
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error assigning points: {e}")
        finally:
            db.close()

def process_message_queue():
    """Process and send messages from the queue."""
    while True:
        try:
            message = message_queue.get()
            if message:
                send_notification_message(
                    updater.bot,
                    chat_id=message["chat_id"],
                    text=message["text"],
                )
                logger.info(f"📨 Sent notification to chat ID {message['chat_id']}.")
        except Exception as e:
            logger.error(f"❌ Error sending queued message: {e}")

def initialize_bot():
    """Initialize the Telegram bot and related services."""
    logger.info("Initializing bot...")

    # Initialize the database (create tables if they don't exist)
    try:
        init_db()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize the database: {e}")
        return

    # Ensure a Configuration row exists
    db = SessionLocal()
    try:
        config = db.query(Configuration).first()
        if not config:
            config = Configuration(active_user_id=None)
            db.add(config)
            db.commit()
            logger.info("✅ Created default Configuration row.")
    except Exception as e:
        logger.error(f"❌ Failed to ensure Configuration row: {e}")
    finally:
        db.close()

    # Validate essential environment variables
    if not all([TOKEN, BOT_USERNAME, WEBHOOK_URL]):
        logger.error("❌ TELEGRAM_BOT_TOKEN, BOT_USERNAME, and WEBHOOK_URL must be set in environment variables.")
        return

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("active_user", active_user))
    dispatcher.add_handler(MessageHandler(Filters.contact, register_contact))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, collect_name))
    dispatcher.add_handler(CallbackQueryHandler(check_balance_callback, pattern="^check_balance$"))
    dispatcher.add_handler(CallbackQueryHandler(redeem_rewards_callback, pattern="^redeem_rewards$"))
    dispatcher.add_handler(CallbackQueryHandler(process_reward_selection, pattern="^redeem_"))
    dispatcher.add_handler(CallbackQueryHandler(view_events, pattern="^view_events$"))
    dispatcher.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))
    dispatcher.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    dispatcher.add_handler(CallbackQueryHandler(event_details, pattern="^event_"))
    dispatcher.add_handler(CallbackQueryHandler(view_disposal_history_callback, pattern="^view_disposal_history$"))

    # Register the error handler
    dispatcher.add_error_handler(error_handler)

    # Set the webhook (Flask route will handle incoming updates)
    try:
        updater.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}/{TOKEN}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        return

    # Initialize the MQTT client
    try:
        mqtt_client = MQTTClientHandler(
            broker_url=MQTT_BROKER_URL,
            broker_port=MQTT_BROKER_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            topic=MQTT_TOPIC,
            message_queue=message_queue,
        )
        logger.info("✅ MQTT client initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MQTT client: {e}")
        return

    # Start the message queue processing in a separate thread
    threading.Thread(target=process_message_queue, daemon=True).start()

    logger.info("✅ Bot is running with webhook and Flask managed by Render.")


# Remove the background thread and call initialize_bot() directly
if __name__ == "__main__":
    # Initialize the bot
    initialize_bot()

    # Start the Flask app (used when running locally with `python bot.py`)
    app.run(host="0.0.0.0", port=PORT)
