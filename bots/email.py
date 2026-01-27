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
                    <title>Chatbot Account Activated</title>
                    </head>

                    <body style="margin:0; padding:0; background-color:#f6f6f6; font-family:Arial, Helvetica, sans-serif;">

                    <table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 10px;">
                    <tr>
                    <td align="center">

                    <!-- Main Container -->
                    <table width="600" cellpadding="0" cellspacing="0"
                        style="max-width:600px; background:#ffffff; border-radius:10px;
                                box-shadow:0 6px 20px rgba(0,0,0,0.08); overflow:hidden;">

                        <!-- Header -->
                        <tr>
                            <td style="background:linear-gradient(135deg, rgb(255,60,0), rgb(175,20,0));
                                    padding:32px; text-align:center;">
                                <h1 style="margin:0; color:#ffffff; font-size:26px; font-weight:600;">
                                    Chatbot Account Activated
                                </h1>
                                <p style="margin-top:10px; color:#ffe3da; font-size:15px;">
                                    Your Redback chatbot is ready for use
                                </p>
                            </td>
                        </tr>

                        <!-- Content -->
                        <tr>
                            <td style="padding:35px; color:#333333;">

                                <p style="font-size:16px; margin:0 0 16px;">
                                    Dear <strong>{owner.username}</strong>,
                                </p>

                                <p style="font-size:15px; line-height:1.7; margin:0 0 28px;">
                                    Your chatbot account has been created successfully.
                                    You can now manage your chatbot, configure settings,
                                    and monitor conversations through your dashboard.
                                </p>

                                <!-- Steps Box -->
                                <table width="100%" cellpadding="0" cellspacing="0"
                                    style="background:#fff3ef; border-left:4px solid rgb(255,60,0);
                                            border-radius:6px; margin-bottom:30px;">
                                    <tr>
                                        <td style="padding:20px;">
                                            <h3 style="margin:0 0 12px; color:rgb(175,20,0); font-size:17px;">
                                                Next Steps
                                            </h3>
                                            <ul style="margin:0; padding-left:20px; font-size:14px; line-height:1.8;">
                                                <li>Contact Redback to receive your credentials</li>
                                                <li>Access your dashboard</li>
                                                <li>Configure your chatbot</li>
                                                <li>Start managing customer interactions</li>
                                            </ul>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Dashboard Button -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:35px;">
                                    <tr>
                                        <td align="center">
                                            <a href="{request.build_absolute_uri('/dashboard/')}"
                                            style="background:rgb(255,60,0); color:#ffffff;
                                                    text-decoration:none; padding:14px 34px;
                                                    font-size:15px; font-weight:600;
                                                    border-radius:6px; display:inline-block;">
                                                Access Dashboard
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Support Section -->
                                <table width="100%" cellpadding="0" cellspacing="0"
                                    style="background:#fffaf8; border:1px solid #ffd1c4;
                                            border-radius:8px;">
                                    <tr>
                                        <td style="padding:22px;">
                                            <h3 style="margin:0 0 12px; font-size:16px; color:rgb(67,26,0);">
                                                Support & Contact
                                            </h3>

                                            <p style="font-size:14px; line-height:1.6; margin:0 0 20px; color:#444;">
                                                If you have any questions or need assistance, please don't hesitate
                                                to contact our support team at Redback.
                                            </p>

                                            <!-- Buttons Grid -->
                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td align="center" style="padding:6px;">
                                                        <a href="tel:8189985555"
                                                        style="background:rgb(217,38,0); color:#ffffff;
                                                                padding:12px 18px; text-decoration:none;
                                                                border-radius:5px; font-size:14px;
                                                                display:inline-block; width:100%; max-width:220px;">
                                                            Call: 81899 85555
                                                        </a>
                                                    </td>
                                                    <td align="center" style="padding:6px;">
                                                        <a href="tel:8189985554"
                                                        style="background:rgb(217,38,0); color:#ffffff;
                                                                padding:12px 18px; text-decoration:none;
                                                                border-radius:5px; font-size:14px;
                                                                display:inline-block; width:100%; max-width:220px;">
                                                            Call: 81899 85554
                                                        </a>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td align="center" style="padding:6px;">
                                                        <a href="https://wa.me/918189985555"
                                                        style="background:rgb(175,20,0); color:#ffffff;
                                                                padding:12px 18px; text-decoration:none;
                                                                border-radius:5px; font-size:14px;
                                                                display:inline-block; width:100%; max-width:220px;">
                                                            WhatsApp Support
                                                        </a>
                                                    </td>
                                                    <td align="center" style="padding:6px;">
                                                        <a href="mailto:info@redback.in"
                                                        style="background:rgb(67,26,0); color:#ffffff;
                                                                padding:12px 18px; text-decoration:none;
                                                                border-radius:5px; font-size:14px;
                                                                display:inline-block; width:100%; max-width:220px;">
                                                            Email: info@redback.in
                                                        </a>
                                                    </td>
                                                </tr>
                                            </table>

                                        </td>
                                    </tr>
                                </table>

                                <!-- Signature -->
                                <p style="margin-top:35px; font-size:15px;">
                                    Best regards,<br>
                                    <strong>Redback Team</strong>
                                </p>

                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background:#f2f2f2; padding:18px; text-align:center;
                                    font-size:12px; color:#777;">
                                This is an automated notification.<br>
                                © Redback AI. All rights reserved.
                            </td>
                        </tr>

                    </table>
                    <!-- End Container -->

                    </td>
                    </tr>
                    </table>

                    </body>
                    </html>
                    """


        
        # Send the email
        from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
        send_async_email(subject, text_message, from_email, [owner.email], html_message)
        logger.debug(f"[✅] Bot activation email queued to: {owner.email}")
        
    except Exception as e:
        logger.error(f"[❌] Failed to send email for bot {bot.name}: {str(e)}")

