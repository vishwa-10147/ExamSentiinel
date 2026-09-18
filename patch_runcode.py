import sys
import re

with open(r'frontend\components\exam\QuestionCard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure apiClient is imported
if 'import { apiClient }' not in text:
    text = text.replace('import { QuestionCandidate } from "@/services/examService";', 
                        'import { QuestionCandidate } from "@/services/examService";\nimport { apiClient } from "@/services/apiClient";')

# Replace the runCode fetch block
old_fetch = r'''      const res = await fetch\("http://localhost:8000/api/sandbox/execute", \{
        method: "POST",
        headers: \{ "Content-Type": "application/json" \},
        body: JSON.stringify\(\{
          language: activeLang,
          code: responseData\.text
        \}\),
      \}\);

      if \(!res\.ok\) \{
        setOutput\(\[`Error: Server returned \$\{res\.status\}`\]\);
        setIsExecuting\(false\);
        return;
      \}
      
      const data = await res\.json\(\);'''

new_fetch = '''      // Ensure we extract session_id from URL or pass it down. 
      // For now, we assume window.location parsing or it's fetched. 
      // Actually, QuestionCard doesn't know session_id. Let's just pull it from pathname.
      const sessionId = window.location.pathname.split("/").pop();
      
      const data = await apiClient.post("/api/code/execute", {
        session_id: sessionId,
        question_id: question.id,
        language: activeLang,
        source_code: responseData.text
      });'''

text = re.sub(old_fetch, new_fetch, text, flags=re.DOTALL)

with open(r'frontend\components\exam\QuestionCard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
