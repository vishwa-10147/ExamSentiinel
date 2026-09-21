def fix_file(filepath, search_str, replace_str):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    start_idx = text.find(search_str)
    if start_idx == -1:
        print(f"Could not find search_str in {filepath}")
        return
        
    end_idx = text.find('};', start_idx) + 2
    if text[end_idx] == '\\n':
        end_idx += 1
        
    text = text[:start_idx] + replace_str + text[end_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Fixed {filepath}")

# Fix practice page
search = "const handleRunCode = async () => {"
replace = '''const handleRunCode = async () => {
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

fix_file('frontend/app/candidate/practice/page.tsx', search, replace)
fix_file('frontend/app/exam/[id]/lab/page.tsx', search, replace.replace('setActiveTab("console");', '').replace('Dispatching to execution cluster...', 'Dispatching to secure execution cluster...').replace('headers: { "Content-Type": "application/json" },', 'headers: { "Content-Type": "application/json", "Authorization": Bearer \\ },'))

# Fix questions page
search2 = "const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {"
replace2 = '''const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
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
  };'''

fix_file('frontend/app/admin/questions/page.tsx', search2, replace2)

# Fix Navbar
with open('frontend/components/Navbar.tsx', 'r', encoding='utf-8') as f:
    nav_text = f.read()

nav_text = nav_text.replace('</Link>', '</Link>\\n        </div>')
with open('frontend/components/Navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(nav_text)

print("Done")
