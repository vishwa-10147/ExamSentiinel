import os
import re

filepath = 'frontend/app/exam/[id]/lab/page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'const handleRunCode = async \(\) => \{.*?\n  \};', '''const handleRunCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to secure execution cluster..."]);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(\\/api/sandbox/execute, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },
        body: JSON.stringify({ language, source_code: code, stdin: "", time_limit_sec: 5.0, memory_limit_mb: 256 })
      });
      const data = await res.json();
      if (res.ok) {
        setOutput(data.stdout ? data.stdout.split("\\n") : []);
        if (data.stderr) {
          setOutput(prev => [...prev, ...data.stderr.split("\\n")]);
        }
      } else {
        setOutput(["Execution failed.", JSON.stringify(data)]);
      }
    } catch (err) {
      setOutput(["Connection error. Please try again."]);
    } finally {
      setIsRunning(false);
    }
  };''', text, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Rewrote lab page function")
