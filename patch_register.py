import sys

with open(r'frontend\app\auth\register\page.tsx', 'r') as f:
    text = f.read()

old_state = '''  const [password, setPassword] = useState("");
  
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);'''

new_state = '''  const [password, setPassword] = useState("");
  
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);'''

text = text.replace(old_state, new_state)

old_submit = '''    if (!firstName || !lastName || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setIsSubmitting(true);'''

new_submit = '''    if (!firstName || !lastName || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    
    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    // SPAM PROTECTION: Requires valid Turnstile token in production
    // if (process.env.NODE_ENV === "production" && !turnstileToken) {
    //   setError("Please complete the security check.");
    //   return;
    // }

    setIsSubmitting(true);'''

text = text.replace(old_submit, new_submit)

old_form = '''            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-lg flex items-start text-sm">
                <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button'''

new_form = '''            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-lg flex items-start text-sm">
                <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* SPAM/BOT PROTECTION STUB */}
            <div className="w-full flex justify-center py-2">
              <div className="w-[300px] h-[65px] bg-slate-100 rounded border border-slate-200 flex items-center justify-center text-xs text-slate-500">
                [Cloudflare Turnstile Widget Placeholder]
              </div>
            </div>

            <button'''

text = text.replace(old_form, new_form)

with open(r'frontend\app\auth\register\page.tsx', 'w') as f:
    f.write(text)
