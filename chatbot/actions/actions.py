
from typing import List, Dict, Any, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import FollowupAction, SlotSet, ConversationPaused, ConversationResumed
from rasa_sdk.events import SessionStarted, ActionExecuted
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import datetime
import threading
import re
import os
import json
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidateRegistrationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_registration_form"

    def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # Check if the name contains only alphabetic characters and spaces
        if len(slot_value) < 2 or not all(c.isalpha() or c.isspace() for c in slot_value):
            dispatcher.utter_message(text="Please provide a valid name with at least 2 alphabetic characters")
            return {"name": None}
        return {"name": slot_value}

    def validate_email(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if not slot_value or not re.match(r"[^@]+@[^@]+\.[^@]+", slot_value):
            dispatcher.utter_message()
            return {"email": None}
        return {"email": slot_value}
    
    
    def validate_mobile(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        cleaned_value = slot_value.replace(" ", "")     
        if not cleaned_value.isdigit() or len(cleaned_value) != 10 or not cleaned_value.startswith(('6', '7', '8', '9')):
            dispatcher.utter_message(text="Please provide a valid Indian mobile number with exactly 10 digits.")
            return {"mobile": None}
        return {"mobile": cleaned_value}



    def validate_country_code(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        country_codes = {
            "+91": "India", "+1": "USA", "+44": "UK", "+81": "Japan", "+61": "Australia",
            "+49": "Germany", "+33": "France", "+39": "Italy", "+86": "China", "+7": "Russia"
        }
        if slot_value not in country_codes:
            dispatcher.utter_message(text="Please provide a valid country code. Example: +91 for India")
            return {"country_code": None}
        dispatcher.utter_message()
        return {"country_code": slot_value}    

    def validate_free_day(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if len(slot_value) < 3:
            dispatcher.utter_message(text="Please provide a valid day for availability.")
            return {"free_day": None}
        return {"free_day": slot_value}

    def validate_available_time(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if len(slot_value) < 3:
            dispatcher.utter_message(text="Please provide a valid time for availability.")
            return {"available_time": None}
        return {"available_time": slot_value}

    def validate_querry(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if len(slot_value) < 5:
            dispatcher.utter_message(text="Please provide a valid querry for the MLM software.")
            return {"querry": None}
        return {"querry": slot_value}

class ActionRegisterUser(Action):
    def name(self) -> str:
        return "submit_registration_form"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Extract slots
        name = tracker.get_slot("name")
        email = tracker.get_slot("email")
        mobile = tracker.get_slot("mobile")
        country_code = tracker.get_slot("country_code")
        free_day = tracker.get_slot("free_day")
        available_time = tracker.get_slot("available_time")
        query = tracker.get_slot("querry")

        logger.info(
            f"Extracted slots - Name: {name}, Email: {email}, Mobile: {mobile}, "
            f"Country Code: {country_code}, Free Day: {free_day}, Available Time: {available_time}, Query: {query}"
        )

        # Validate email
        if not self.is_valid_email(email):
            dispatcher.utter_message(text="The email you entered is invalid. Please provide a valid email address.")
            return [SlotSet("email", None)]

        # Generate session ID and timestamp
        session_id = self.generate_session_id(email)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Start threads for saving chat and sending email
        chat_thread = threading.Thread(target=self.save_chat_and_send_email, args=(tracker, session_id, name, email, timestamp))
        chat_thread.start()

        dispatcher.utter_message(text="Thanks for the details, Our team will reach out to you very soon.")

        # Reset slots and session
        return [
            SlotSet("name", None),
            SlotSet("email", None),
            SlotSet("mobile", None),
            SlotSet("country_code", None),
            SlotSet("free_day", None),
            SlotSet("available_time", None),
            SlotSet("querry", None),
            ConversationPaused(),
            SessionStarted(),
            ActionExecuted("action_session_start"),
        ]

    @staticmethod
    def is_valid_email(email: str) -> bool:
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(email_regex, email) is not None

    @staticmethod
    def generate_session_id(unique_data: str) -> str:
        return hashlib.md5(unique_data.encode()).hexdigest()

    def save_chat_and_send_email(self, tracker: Tracker, session_id: str, user_name: str, user_email: str, timestamp: str) -> None:
        folder_path = "user_chats"
        os.makedirs(folder_path, exist_ok=True)

        # Generate sanitized file name
        sanitized_name = re.sub(r"[^\w\s]", "", user_name).replace(" ", "_")
        file_name = f"{sanitized_name}_{timestamp}_chat.json"
        file_path = os.path.join(folder_path, file_name)

        try:
            # Save chat history
            chat_history = [
                {"user_message": e.get("text"), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                if e.get("event") == "user"
                else {"bot_message": e.get("text"), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                for e in tracker.events if e.get("event") in {"user", "bot"}
            ]
            chat_history.append({"query": tracker.get_slot("querry"), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

            with open(file_path, "w") as chat_file:
                json.dump(chat_history, chat_file, indent=4)
            logger.info(f"Chat saved to {file_path}")

            # Send email
            self.send_email_with_chat(file_path, user_name, user_email)
        except Exception as e:
            logger.error(f"Error in saving chat or sending email: {e}")

    def send_email_with_chat(self, file_path: str, user_name: str, user_email: str) -> None:
        smtp_server = "smtp.zoho.com"
        smtp_port = 587
        sender_email = "ashish.py@maxtratechnologies.net"
        sender_password = "iwfenP1dMKMz"
        receiver_email = "shivendra@maxtratechnologies.com"

        subject = f"Chat History for {user_name}"
        body = f"Hello,\n\nAttached is the chat history for the user session.\n\nBest regards,\nYour Bot"

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
                msg.attach(part)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
            logger.info(f"Email sent to {receiver_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")


class ActionResumeConversation(Action):
    def name(self) -> Text:
        return "action_resume_conversation"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict]:
        dispatcher.utter_message(text="Conversation resumed. How can I assist you?")
        return [ConversationResumed()]