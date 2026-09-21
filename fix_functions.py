import os

# Fix questions page
with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Find from 'const handleFileUpload' to '};'
text = re.sub(r'const handleFileUpload = async \(event: React\.ChangeEvent<HTMLInputElement>\) => \{.*?\n  \};', '''const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploadingCSV(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(\\/api/questions/bulk, {
        method: "POST",
        headers: { "Authorization": Bearer \\ },
        body: formData,
      });
      if (res.ok) {
        toast.success("Questions imported successfully!");
        const data = await apiClient.get("/api/questions");
        setQuestions(data);
      } else {
        toast.error("Failed to import CSV.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error uploading CSV.");
    } finally {
      setIsUploadingCSV(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };''', text, flags=re.DOTALL)

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

# Fix practice page
with open('frontend/app/candidate/practice/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'const handleRunCode = async \(\) => \{.*?\n  \};', '''const handleRunCode = async () => {
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
  };''', text, flags=re.DOTALL)

with open('frontend/app/candidate/practice/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print("Rewrote functions")
