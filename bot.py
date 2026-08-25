import os
import logging
import math
import datetime
import re
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
UNITS = {
    'Length': {
        'meters': 1, 'kilometers': 1000, 'centimeters': 0.01, 
        'millimeters': 0.001, 'miles': 1609.34, 'yards': 0.9144,
        'feet': 0.3048, 'inches': 0.0254
    },
    'Weight': {
        'kilograms': 1, 'grams': 0.001, 'pounds': 0.453592,
        'ounces': 0.0283495, 'tons': 1000
    }
}

DATA_SIZES = {
    'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3,
    'TB': 1024**4, 'PB': 1024**5
}

class CalculatorBot:
    def __init__(self):
        self.user_data = {}

    def calculate_basic(self, expression: str) -> str:
        """Basic arithmetic calculations"""
        try:
            # Remove any dangerous characters
            expression = re.sub(r'[^0-9+\-*/().%\s]', '', expression)
            # Replace percentage
            expression = expression.replace('%', '/100')
            result = eval(expression)
            return f"Result: {result:.2f}" if isinstance(result, float) else f"Result: {result}"
        except Exception as e:
            return f"Error: Invalid expression. Please use basic operators (+, -, *, /, %, parentheses)"

    def calculate_percentage(self, value: float, percentage: float) -> str:
        """Calculate percentage of a value"""
        result = (value * percentage) / 100
        return f"{percentage}% of {value} = {result:.2f}"

    def calculate_discount(self, price: float, discount: float) -> str:
        """Calculate discounted price"""
        if discount > 100:
            return "Error: Discount cannot exceed 100%"
        discount_amount = (price * discount) / 100
        final_price = price - discount_amount
        return f"Original: ${price:.2f}\nDiscount: {discount}%\nDiscount Amount: ${discount_amount:.2f}\nFinal Price: ${final_price:.2f}"

    def calculate_compound_interest(self, principal: float, rate: float, time: float, n: int = 12) -> str:
        """Calculate compound interest"""
        if rate > 100:
            return "Error: Interest rate cannot exceed 100%"
        amount = principal * (1 + (rate/100)/n) ** (n * time)
        interest = amount - principal
        return f"Principal: ${principal:.2f}\nRate: {rate}%\nTime: {time} years\nCompound frequency: {n} times/year\n\nTotal Amount: ${amount:.2f}\nTotal Interest: ${interest:.2f}"

    def convert_unit(self, value: float, from_unit: str, to_unit: str, category: str) -> str:
        """Convert between units"""
        try:
            if category not in UNITS:
                return "Error: Unit category not found"
            
            units = UNITS[category]
            if from_unit not in units or to_unit not in units:
                return "Error: Unit not found in category"
            
            # Convert to base unit (meters or kilograms)
            base_value = value * units[from_unit]
            # Convert from base unit to target unit
            result = base_value / units[to_unit]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"
        except Exception as e:
            return f"Error: {str(e)}"

    def convert_data_size(self, value: float, from_unit: str, to_unit: str) -> str:
        """Convert data sizes"""
        try:
            from_unit = from_unit.upper()
            to_unit = to_unit.upper()
            if from_unit not in DATA_SIZES or to_unit not in DATA_SIZES:
                return "Error: Invalid data size unit"
            
            # Convert to bytes
            bytes_value = value * DATA_SIZES[from_unit]
            # Convert from bytes to target unit
            result = bytes_value / DATA_SIZES[to_unit]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"
        except Exception as e:
            return f"Error: {str(e)}"

    def calculate_bmi(self, weight: float, height: float, unit: str = 'metric') -> str:
        """Calculate BMI"""
        try:
            if unit == 'metric':
                bmi = weight / (height ** 2)
            else:  # imperial
                bmi = (weight / (height ** 2)) * 703
            
            bmi = round(bmi, 1)
            
            # BMI categories
            if bmi < 18.5:
                category = "Underweight"
            elif bmi < 25:
                category = "Normal weight"
            elif bmi < 30:
                category = "Overweight"
            else:
                category = "Obese"
            
            return f"BMI: {bmi}\nCategory: {category}\n\nNote: BMI is a screening tool, not a diagnostic measure."
        except Exception as e:
            return f"Error: {str(e)}"

    def calculate_age(self, birth_date_str: str) -> str:
        """Calculate age from birth date"""
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    birth_date = datetime.datetime.strptime(birth_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                return "Error: Invalid date format. Please use YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY"
            
            today = datetime.date.today()
            
            # Check if birth date is in the future
            if birth_date > today:
                return "Error: Birth date cannot be in the future"
            
            # Calculate age
            years = today.year - birth_date.year
            months = today.month - birth_date.month
            days = today.day - birth_date.day
            
            if days < 0:
                months -= 1
                # Get days in previous month
                prev_month = today.replace(day=1) - datetime.timedelta(days=1)
                days += prev_month.day
                
            if months < 0:
                years -= 1
                months += 12
            
            # Calculate next birthday
            try:
                next_birthday = birth_date.replace(year=today.year + 1)
            except ValueError:
                # Handle leap year Feb 29
                next_birthday = birth_date.replace(year=today.year + 1, month=3, day=1)
            
            days_to_birthday = (next_birthday - today).days
            
            return f"Age: {years} years, {months} months, {days} days\nDays until next birthday: {days_to_birthday}\nTotal days alive: {(today - birth_date).days}"
        except Exception as e:
            return f"Error: {str(e)}"

    def calculate_date_diff(self, date1_str: str, date2_str: str) -> str:
        """Calculate difference between two dates"""
        try:
            # Try different date formats
            def parse_date(date_str):
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        return datetime.datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                raise ValueError("Invalid date format")
            
            date1 = parse_date(date1_str)
            date2 = parse_date(date2_str)
            
            if date1 == date2:
                return "The dates are the same"
            
            diff = abs(date2 - date1)
            days = diff.days
            years = days // 365
            months = (days % 365) // 30
            remaining_days = (days % 365) % 30
            
            return f"Difference: {years} years, {months} months, {remaining_days} days\nTotal days: {days}"
        except Exception as e:
            return f"Error: {str(e)}"

# Initialize bot
bot = CalculatorBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when /start is issued."""
    user = update.effective_user
    welcome_message = f"""
👋 Hello {user.first_name}! Welcome to Calculator Bot!

I can help you with various calculations. Here's what I can do:

🧮 Basic Calculations: 2+2, 10*5, (4+3)*2
📊 Percentages: 20% of 100
🏷️ Discounts: 100 with 20% off
💰 Compound Interest: Principal, Rate, Time
📏 Unit Conversions: Length, Weight
💾 Data-size Conversions: KB, MB, GB, TB
📊 BMI Calculator
🎂 Age Calculator
📅 Date Calculator

🔧 To use me:
- For basic math, just send me an expression
- For other features, use the menu below or type /help

🚀 Let's start calculating!
"""
    
    # Create inline keyboard with options
    keyboard = [
        [InlineKeyboardButton("🧮 Basic Calc", callback_data='calc_basic'),
         InlineKeyboardButton("📊 Percentage", callback_data='calc_percentage')],
        [InlineKeyboardButton("🏷️ Discount", callback_data='calc_discount'),
         InlineKeyboardButton("💰 Compound Interest", callback_data='calc_compound')],
        [InlineKeyboardButton("📏 Unit Convert", callback_data='convert_unit'),
         InlineKeyboardButton("💾 Data-size Convert", callback_data='convert_data')],
        [InlineKeyboardButton("📊 BMI", callback_data='calc_bmi'),
         InlineKeyboardButton("🎂 Age Calculator", callback_data='calc_age')],
        [InlineKeyboardButton("📅 Date Calculator", callback_data='calc_date')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when /help is issued."""
    help_text = """
🤖 **Calculator Bot Help**

**Basic Calculations:**
Simply type any arithmetic expression: `2+2`, `10*5`, `(4+3)*2`, `10%`

**Percentage Calculator:**
Type: `percentage 20 of 100` or use the button

**Discount Calculator:**
Type: `discount 100 with 20%` or use the button

**Compound Interest:**
Type: `compound 1000 5 2` (principal, rate%, time in years)
Optional: `compound 1000 5 2 12` (monthly compounding)

**Unit Conversions:**
Type: `convert 10 meters to feet` or use the button
Available units: meters, km, cm, mm, miles, yards, feet, inches

**Data-size Conversions:**
Type: `datasize 1024 MB to GB` or use the button
Available units: B, KB, MB, GB, TB, PB

**BMI Calculator:**
Type: `bmi 70 1.75` (weight in kg, height in meters)
Or: `bmi 154 5'10"` (weight in lbs, height in imperial)

**Age Calculator:**
Type: `age 1990-01-01` or use the button
Formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY

**Date Calculator:**
Type: `datediff 2024-01-01 to 2024-12-31` or use the button

**Commands:**
/start - Start the bot
/help - Show this help message
/menu - Show the main menu

💡 **Tips:**
- Use the buttons for guided calculations
- Send any number/expression for quick calculation
- All calculations are done with high precision
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the main menu."""
    keyboard = [
        [InlineKeyboardButton("🧮 Basic Calc", callback_data='calc_basic'),
         InlineKeyboardButton("📊 Percentage", callback_data='calc_percentage')],
        [InlineKeyboardButton("🏷️ Discount", callback_data='calc_discount'),
         InlineKeyboardButton("💰 Compound Interest", callback_data='calc_compound')],
        [InlineKeyboardButton("📏 Unit Convert", callback_data='convert_unit'),
         InlineKeyboardButton("💾 Data-size Convert", callback_data='convert_data')],
        [InlineKeyboardButton("📊 BMI", callback_data='calc_bmi'),
         InlineKeyboardButton("🎂 Age Calculator", callback_data='calc_age')],
        [InlineKeyboardButton("📅 Date Calculator", callback_data='calc_date')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 **Main Menu**\nSelect a calculation type:", parse_mode='Markdown', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Store the current operation in user context
    context.user_data['operation'] = query.data
    
    # Define operation messages
    messages = {
        'calc_basic': "🧮 **Basic Calculator**\n\nSend me any arithmetic expression.\nExample: `2+2`, `10*5`, `(4+3)*2`",
        'calc_percentage': "📊 **Percentage Calculator**\n\nSend me the value and percentage.\nExample: `percentage 20 of 100`",
        'calc_discount': "🏷️ **Discount Calculator**\n\nSend me the price and discount.\nExample: `discount 100 with 20%`",
        'calc_compound': "💰 **Compound Interest Calculator**\n\nSend me principal, rate, and time.\nExample: `compound 1000 5 2` (principal=1000, rate=5%, time=2 years)",
        'convert_unit': "📏 **Unit Converter**\n\nSend me the conversion.\nExample: `convert 10 meters to feet`",
        'convert_data': "💾 **Data-size Converter**\n\nSend me the data size.\nExample: `datasize 1024 MB to GB`",
        'calc_bmi': "📊 **BMI Calculator**\n\nSend me weight and height.\nMetric: `bmi 70 1.75` (kg, meters)\nImperial: `bmi 154 5'10\"` (lbs, feet'inches\")",
        'calc_age': "🎂 **Age Calculator**\n\nSend me your birth date.\nExample: `age 1990-01-01`",
        'calc_date': "📅 **Date Calculator**\n\nSend me two dates.\nExample: `datediff 2024-01-01 to 2024-12-31`",
        'help': "ℹ️ **Help**\n\nType /help for detailed instructions"
    }
    
    message = messages.get(query.data, "Please use the /help command for instructions.")
    await query.edit_message_text(message, parse_mode='Markdown')
    
    if query.data == 'calc_basic':
        context.user_data['awaiting_input'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages."""
    user_input = update.message.text.strip()
    response = None
    operation = context.user_data.get('operation', '')
    context.user_data['awaiting_input'] = False
    
    # Check if it's a basic calculation (without any command prefix)
    if not any(user_input.lower().startswith(cmd) for cmd in ['percentage', 'discount', 'compound', 'convert', 'datasize', 'bmi', 'age', 'datediff']):
        # Try basic calculation
        try:
            result = bot.calculate_basic(user_input)
            if not result.startswith('Error'):
                await update.message.reply_text(f"🧮 **Result**\n\n{result}", parse_mode='Markdown')
                return
        except:
            pass
    
    # Process based on operation or direct input
    try:
        if user_input.lower().startswith('percentage') or operation == 'calc_percentage':
            parts = user_input.split()
            if len(parts) >= 4 and parts[2].lower() == 'of':
                value = float(parts[1])
                percentage = float(parts[3])
                result = bot.calculate_percentage(value, percentage)
                response = f"📊 **Percentage Calculator**\n\n{result}"
            
        elif user_input.lower().startswith('discount') or operation == 'calc_discount':
            parts = user_input.split()
            if 'with' in user_input and '%' in user_input:
                # Extract price and discount from the string
                price_match = re.search(r'\d+\.?\d*', user_input)
                discount_match = re.search(r'(\d+\.?\d*)%', user_input)
                if price_match and discount_match:
                    price = float(price_match.group())
                    discount = float(discount_match.group(1))
                    result = bot.calculate_discount(price, discount)
                    response = f"🏷️ **Discount Calculator**\n\n{result}"
        
        elif user_input.lower().startswith('compound') or operation == 'calc_compound':
            parts = user_input.split()
            if len(parts) >= 4:
                principal = float(parts[1])
                rate = float(parts[2])
                time = float(parts[3])
                n = 12  # Default monthly compounding
                if len(parts) >= 5:
                    n = int(parts[4])
                result = bot.calculate_compound_interest(principal, rate, time, n)
                response = f"💰 **Compound Interest Calculator**\n\n{result}"
        
        elif user_input.lower().startswith('convert') or operation == 'convert_unit':
            parts = user_input.lower().split()
            if len(parts) >= 4 and parts[2] == 'to':
                value = float(parts[1])
                from_unit = parts[2] if len(parts) > 3 else parts[3]
                to_unit = parts[-1]
                # Determine category
                category = 'Length' if from_unit in UNITS['Length'] or to_unit in UNITS['Length'] else 'Weight'
                result = bot.convert_unit(value, from_unit, to_unit, category)
                response = f"📏 **Unit Converter**\n\n{result}"
        
        elif user_input.lower().startswith('datasize') or operation == 'convert_data':
            parts = user_input.upper().split()
            if len(parts) >= 4 and parts[3] == 'TO':
                value = float(parts[1])
                from_unit = parts[2]
                to_unit = parts[4] if len(parts) > 4 else parts[-1]
                result = bot.convert_data_size(value, from_unit, to_unit)
                response = f"💾 **Data-size Converter**\n\n{result}"
        
        elif user_input.lower().startswith('bmi') or operation == 'calc_bmi':
            if "'" in user_input or '"' in user_input:
                # Imperial format: bmi 154 5'10"
                parts = user_input.split()
                if len(parts) >= 3:
                    weight = float(parts[1])
                    height_parts = parts[2].replace('"', '').split("'")
                    if len(height_parts) == 2:
                        feet = float(height_parts[0])
                        inches = float(height_parts[1])
                        height = (feet * 12 + inches) / 12  # Convert to feet
                        result = bot.calculate_bmi(weight, height, unit='imperial')
                        response = f"📊 **BMI Calculator (Imperial)**\n\n{result}"
            else:
                # Metric format: bmi 70 1.75
                parts = user_input.split()
                if len(parts) >= 3:
                    weight = float(parts[1])
                    height = float(parts[2])
                    result = bot.calculate_bmi(weight, height)
                    response = f"📊 **BMI Calculator (Metric)**\n\n{result}"
        
        elif user_input.lower().startswith('age') or operation == 'calc_age':
            parts = user_input.split()
            if len(parts) >= 2:
                birth_date = parts[1]
                result = bot.calculate_age(birth_date)
                response = f"🎂 **Age Calculator**\n\n{result}"
        
        elif user_input.lower().startswith('datediff') or operation == 'calc_date':
            parts = user_input.split()
            if 'to' in user_input:
                date_parts = user_input.replace('datediff', '').strip().split('to')
                if len(date_parts) >= 2:
                    date1 = date_parts[0].strip()
                    date2 = date_parts[1].strip()
                    result = bot.calculate_date_diff(date1, date2)
                    response = f"📅 **Date Calculator**\n\n{result}"
        
        # If no specific operation matched, try basic calculation again
        if response is None:
            try:
                result = bot.calculate_basic(user_input)
                if not result.startswith('Error'):
                    response = f"🧮 **Result**\n\n{result}"
                else:
                    response = "❌ I couldn't understand your input. Please use /help to see available commands."
            except:
                response = "❌ I couldn't understand your input. Please use /help to see available commands."
        
        if response:
            await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    # Get token from environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
    
    # Create Application
    application = Application.builder().token(token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu))

    # Callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Message handler for user input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
