import re

with open("frontend/app/candidate/practice/page.tsx", "r", encoding="utf-8") as f:
    prac = f.read()
prac = re.sub(r'const runCode = async \(\) => \{.*?\n  \};', '''const runCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to execution cluster..."]);
    setActiveTab("console");
    try {
      const res = await fetch(\\/api/sandbox/execute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: language, source_code: code, stdin: "", time_limit_sec: 5.0, memory_limit_mb: 256 })
      });
      const data = await res.json();
      if (res.ok) {
        setOutput(data.stdout ? data.stdout.split("\\n") : []);
        if (data.stderr) setOutput(prev => [...prev, ...data.stderr.split("\\n")]);
      } else {
        setOutput(["Execution failed.", JSON.stringify(data)]);
      }
    } catch (err) {
      setOutput(["Connection error. Please try again."]);
    } finally {
      setIsRunning(false);
    }
  };''', prac, flags=re.DOTALL)
with open("frontend/app/candidate/practice/page.tsx", "w", encoding="utf-8") as f:
    f.write(prac)

print("Practice fixed")
