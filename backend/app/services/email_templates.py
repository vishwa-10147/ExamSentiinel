"\""HTML Email Templates for ExamSentinel.\""\""

def get_base_template(content: str) -> str:
    return f\"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #6b7280; }}
            .btn {{ display: inline-block; padding: 10px 20px; background-color: #2563eb; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>ExamSentinel</h2>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>This is an automated message from the ExamSentinel platform.</p>
                <p>&copy; 2026 ExamSentinel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    \"""

def get_welcome_template(full_name: str, email: str, plain_password: str, login_url: str) -> str:
    content = f\"""
        <h3>Welcome to ExamSentinel, {full_name}!</h3>
        <p>An account has been created for you on the ExamSentinel platform.</p>
        <p>Your login credentials are:</p>
        <ul>
            <li><strong>Email:</strong> {email}</li>
            <li><strong>Password:</strong> {plain_password}</li>
        </ul>
        <p>Please log in and change your password immediately.</p>
        <div style="text-align: center;">
            <a href="{login_url}" class="btn">Log In to ExamSentinel</a>
        </div>
    \"""
    return get_base_template(content)

def get_results_published_template(full_name: str, exam_name: str, results_url: str) -> str:
    content = f\"""
        <h3>Exam Results Published</h3>
        <p>Dear {full_name},</p>
        <p>The results for <strong>{exam_name}</strong> have been published.</p>
        <p>You can now log in to view your score, detailed breakdown, and leaderboard ranking.</p>
        <div style="text-align: center;">
            <a href="{results_url}" class="btn">View My Results</a>
        </div>
    \"""
    return get_base_template(content)

def get_custom_broadcast_template(content: str) -> str:
    return get_base_template(content)
