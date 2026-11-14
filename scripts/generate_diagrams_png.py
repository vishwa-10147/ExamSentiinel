import base64
import urllib.request
import os

diagrams = {
    "1_architecture": """flowchart TD
    subgraph Client ["Client Side (Next.js 14)"]
        UI["Candidate & Admin Portals"]
        WebRTC["WebRTC Audio/Video Capture"]
        Editor["Monaco Code Editor"]
    end
    subgraph Comm ["Communication Layer"]
        REST["REST API (HTTPS)"]
        WS["WebSockets (WSS)"]
    end
    subgraph Backend ["Backend Server (FastAPI)"]
        API_Routes["API Routers"]
        Services["Business Logic & Services"]
        Auth["Security & RBAC"]
    end
    subgraph AI_Engines ["Machine Learning & Execution Engines"]
        YOLO["YOLOv11 (Vision Proctoring)"]
        Whisper["Whisper AI (Interview STT)"]
        Piston["Piston Sandbox (Code Execution)"]
        MOSS["MOSS Winnowing (Plagiarism)"]
    end
    subgraph DB ["Data Storage"]
        Postgres[(PostgreSQL Database)]
    end
    UI --> REST
    UI --> WS
    WebRTC --> WS
    Editor --> REST
    REST --> API_Routes
    WS --> API_Routes
    API_Routes --> Services
    API_Routes --> Auth
    Services --> Postgres
    Services --> YOLO
    Services --> Whisper
    Services --> Piston
    Services --> MOSS
""",
    "2_proctoring_flow": """flowchart LR
    Browser["Candidate Browser"]
    subgraph Telemetry ["Data Capture Module"]
        Frames["Video Frames (Webcam)"]
        Events["Browser Events (Tab Blur, Copy)"]
    end
    subgraph AI_Analysis ["AI Analysis Engine"]
        YOLO["YOLOv11 Model"]
        Detect["Detect: Phone, Book, Person"]
    end
    subgraph Logic ["Decision Engine"]
        Calibrator["Risk Calibrator"]
        Flags["Risk Level (CRITICAL, HIGH)"]
    end
    Dashboard["Reviewer Marking Center"]
    Browser --> Frames
    Browser --> Events
    Frames --> YOLO
    YOLO --> Detect
    Detect --> Calibrator
    Events --> Calibrator
    Calibrator --> Flags
    Flags --> Dashboard
""",
    "3_plagiarism_pipeline": """flowchart LR
    Input["Candidate Source Code"]
    Norm["Normalization (Strip Comments/Spaces)"]
    Kgram["K-gram Generation (Shingling)"]
    Hash["Hashing Function"]
    Window["Sliding Window Analysis"]
    MinHash["Select Minimum Hash (Fingerprints)"]
    Compare["Jaccard Similarity Comparison"]
    Result["Structural Similarity Score (%)"]
    Input --> Norm
    Norm --> Kgram
    Kgram --> Hash
    Hash --> Window
    Window --> MinHash
    MinHash --> Compare
    Compare --> Result
""",
    "4_interview_pipeline": """flowchart TD
    Audio["WebRTC Audio Stream (Mic)"]
    Buffer["Audio Buffering & Compression"]
    Whisper["OpenAI Whisper AI (Speech-to-Text)"]
    Text["Raw Text Transcript"]
    NLP["NLP Semantic Analyzer"]
    Keywords["Extract Technical Keywords (e.g., 'API', 'SQL')"]
    Compare["Compare with Expected Knowledge Base"]
    Score["Topic Coverage Score"]
    Audio --> Buffer
    Buffer --> Whisper
    Whisper --> Text
    Text --> NLP
    NLP --> Keywords
    Keywords --> Compare
    Compare --> Score
"""
}

out_dir = r"d:\vishwa47\v47Studio\ExamSentinel\diagrams"
os.makedirs(out_dir, exist_ok=True)

for name, code in diagrams.items():
    # Base64 encode the mermaid code
    b64_raw = base64.urlsafe_b64encode(code.encode('utf-8')).decode('utf-8')
    # Use mermaid.ink to render the image. Adding bgColor=white makes it clean for documents.
    url = f"https://mermaid.ink/img/{b64_raw}?bgColor=white"
    
    out_path = os.path.join(out_dir, f"{name}.png")
    try:
        print(f"Downloading {name}.png...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(out_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Saved {name}.png successfully.")
    except Exception as e:
        print(f"Failed to download {name}.png: {e}")
