import logging
from django.conf import settings
from utils.email import send_async_email

logger = logging.getLogger(__name__)


def send_bot_activation_email(bot, request):
    """
    Send bot activation email to workspace owner.
    
    Args:
        bot: Bot instance
        request: Django request object for building absolute URIs
    """
    try:
        workspace = bot.workspace
        owner = workspace.owner
        
        logger.debug(f"[⚠️] Sending bot activation email to: {owner.email}")
        
        subject = "Your Chatbot Account Has Been Created"
        
        # Plain text version
        text_message = (
            f"Dear {owner.username},\n\n"
            f"Your chatbot account has been created successfully.\n\n"
            f"Contact Redback to get your credentials and log in to your dashboard to manage your bot.\n\n"
            f"Dashboard: {request.build_absolute_uri('/dashboard/')}\n\n"
            "Best regards,\nRedback Team"
        )
        
        # HTML version
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Chatbot Account Created</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; line-height: 1.6;">
            <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                
                <!-- Header Section -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 40px 30px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;">Account Created Successfully!</h1>
                    <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Your chatbot is ready to use</p>
                </div>
                
                <!-- Content Section -->
                <div style="padding: 40px 30px;">
                    <div style="margin-bottom: 30px;">
                        <p style="font-size: 16px; color: #374151; margin: 0 0 15px 0;">Dear <strong>{owner.username}</strong>,</p>
                        <p style="font-size: 16px; color: #6b7280; margin: 0; line-height: 1.6;">Your chatbot account has been created successfully. You're all set to start managing your bot and enhancing your customer support experience.</p>
                    </div>
                    
                    <!-- Highlights Box -->
                    <div style="background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border-left: 4px solid #2563eb; padding: 25px; margin: 30px 0; border-radius: 0 8px 8px 0;">
                        <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1e40af; font-weight: 600;">Next Steps</h3>
                        <ul style="margin: 0; padding-left: 20px; color: #374151; font-size: 14px; line-height: 1.8;">
                            <li>Contact Redback to receive your credentials</li>
                            <li>Log in to your dashboard with the provided credentials</li>
                            <li>Configure your chatbot settings and preferences</li>
                            <li>Start managing your bot and conversations</li>
                        </ul>
                    </div>
                    
                    <!-- Call to Action -->
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="{request.build_absolute_uri('/dashboard/')}" 
                           style="display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; letter-spacing: 0.3px; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);">
                            Access Your Dashboard
                        </a>
                    </div>
                    
                    <!-- Support Info -->
                    <div style="background-color: #fefce8; border: 1px solid #fde047; border-radius: 8px; padding: 20px; margin: 30px 0;">
                        <h4 style="margin: 0 0 12px 0; font-size: 16px; color: #a16207; font-weight: 600;">Support</h4>
                        <p style="margin: 0; font-size: 14px; color: #92400e; line-height: 1.6;">
                            If you have any questions or need assistance, please don't hesitate to contact our support team at Redback.
                        </p>
                    </div>
                    
                    <div style="margin-top: 40px; padding-top: 30px; border-top: 1px solid #e5e7eb;">
                        <p style="margin: 0 0 8px 0; font-size: 16px; color: #374151;">Best regards,</p>
                        <p style="margin: 0; font-size: 16px; font-weight: 600; color: #111827;">Redback Team</p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f3f4f6; padding: 25px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 12px; color: #6b7280;">
                        This is an automated notification. Your chatbot account is now active.<br>
                        For support, please contact the Redback team.
                    </p>
                </div>
                
            </div>
        </body>
        </html>
        """
        
        # Send the email
        from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
        send_async_email(subject, text_message, from_email, [owner.email], html_message)
        logger.debug(f"[✅] Bot activation email queued to: {owner.email}")
        
    except Exception as e:
        logger.error(f"[❌] Failed to send email for bot {bot.name}: {str(e)}")
