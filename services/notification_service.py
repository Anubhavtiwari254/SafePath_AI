import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)


class NotificationService:
    """Emergency notification dispatch service supporting simulation, SMS, and messaging fallbacks."""

    @classmethod
    def dispatch_emergency_alert(
        cls,
        contacts: List[Dict[str, Any]],
        sender_name: str,
        share_url: str,
        coordinates: Dict[str, float],
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatch emergency notification to configured trusted contacts.
        Does not falsely report success if notifications were simulated.
        """
        lat = coordinates.get("latitude")
        lng = coordinates.get("longitude")
        user_msg = custom_message or "I need assistance. Please see my live emergency location:"
        
        full_message = f"EMERGENCY ALERT from {sender_name}: {user_msg}\nLive Location: {share_url}"
        encoded_message = urllib.parse.quote(full_message)

        # Fallback quick-dispatch links
        native_sms_link = f"sms:?body={encoded_message}"
        native_whatsapp_link = f"https://wa.me/?text={encoded_message}"

        delivery_results = []
        is_mock = Config.SMS_PROVIDER.lower() != "twilio" or not Config.TWILIO_ACCOUNT_SID

        if is_mock:
            # Simulation mode
            logger.info("Notification simulation: Alert for %s: %s", sender_name, full_message)
            for c in contacts:
                c_name = c.get("contact_name", "Trusted Contact")
                c_val = c.get("contact_value", "")
                c_method = c.get("contact_method", "phone")
                delivery_results.append({
                    "contact_name": c_name,
                    "contact_value": c_val,
                    "method": c_method,
                    "status": "simulation_ready",
                    "delivered": False,
                    "status_text": "Simulation Mode: Alert generated. Use 1-Click Native Share / SMS fallback to dispatch to your contact.",
                })
            
            return {
                "success": True,
                "provider": "simulation",
                "is_simulated": True,
                "message_text": full_message,
                "native_sms_url": native_sms_link,
                "whatsapp_url": native_whatsapp_link,
                "delivery_results": delivery_results,
                "summary": "Emergency share link generated. Direct automated carrier delivery was simulated. Please use the WhatsApp, SMS, or native share button to forward immediately."
            }

        # Twilio SMS delivery if configured
        try:
            from twilio.rest import Client
            client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
            all_sent = True

            for c in contacts:
                c_name = c.get("contact_name", "Trusted Contact")
                c_val = c.get("contact_value", "")
                try:
                    message_obj = client.messages.create(
                        body=full_message,
                        from_=Config.TWILIO_PHONE_NUMBER,
                        to=c_val
                    )
                    delivery_results.append({
                        "contact_name": c_name,
                        "contact_value": c_val,
                        "method": "sms",
                        "status": "sent",
                        "delivered": True,
                        "sid": message_obj.sid,
                        "status_text": "SMS confirmed dispatched via Twilio."
                    })
                except Exception as sms_err:
                    all_sent = False
                    logger.error("Twilio SMS send error for %s: %s", c_val, sms_err)
                    delivery_results.append({
                        "contact_name": c_name,
                        "contact_value": c_val,
                        "method": "sms",
                        "status": "failed",
                        "delivered": False,
                        "status_text": f"Carrier delivery failed: {str(sms_err)}"
                    })

            return {
                "success": all_sent,
                "provider": "twilio",
                "is_simulated": False,
                "message_text": full_message,
                "native_sms_url": native_sms_link,
                "whatsapp_url": native_whatsapp_link,
                "delivery_results": delivery_results,
                "summary": "Alert dispatched via Twilio carrier service." if all_sent else "Some alerts could not be delivered directly by carrier."
            }

        except Exception as e:
            logger.error("Failed to initialize Twilio client: %s", e)
            return {
                "success": False,
                "provider": "twilio_error",
                "is_simulated": True,
                "message_text": full_message,
                "native_sms_url": native_sms_link,
                "whatsapp_url": native_whatsapp_link,
                "delivery_results": [
                    {
                        "contact_name": c.get("contact_name"),
                        "contact_value": c.get("contact_value"),
                        "status": "failed",
                        "delivered": False,
                        "status_text": "Carrier service unavailable. Use native share."
                    }
                    for c in contacts
                ],
                "summary": "Carrier alert gateway unavailable. Please use the 1-click WhatsApp/SMS buttons below."
            }
