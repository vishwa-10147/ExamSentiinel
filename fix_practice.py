import os

filepath = 'frontend/app/candidate/practice/page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

search = "const runCode = async () => {"
replace = '''const runCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to execution cluster..."]);
    setActiveTab("console");
    
    try {
      const res = await fetch(\\/api/sandbox/execute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: language,
          source_code: code,
          stdin: "",
          time_limit_sec: 5.0,
          memory_limit_mb: 256
        })
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
  };'''

start_idx = text.find(search)
if start_idx != -1:
    end_idx = text.find('};', start_idx) + 2
    if text[end_idx] == '\\n':
        end_idx += 1
    text = text[:start_idx] + replace + text[end_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Fixed practice page")
