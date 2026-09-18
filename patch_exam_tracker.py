import sys

with open(r'frontend\app\exam\[id]\page.tsx', 'r') as f:
    text = f.read()

import_face = 'import FaceTracker from "@/components/FaceTracker";'
text = text.replace('import { SubmitModal } from "@/components/exam/SubmitModal";', 'import { SubmitModal } from "@/components/exam/SubmitModal";\n' + import_face)

handle_ai_event = '''  const handleAIEvent = useCallback((eventType: string, details: any) => {
    if (session) {
      proctoringService.logEvent(session.id, eventType, details);
    }
  }, [session]);'''

text = text.replace('const handleResponseChange = (', handle_ai_event + '\n\n  const handleResponseChange = (')

# Place FaceTracker in the sidebar below the QuestionPalette
old_sidebar = '''          {/* Right Sidebar: Palette */}
          <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
            <QuestionPalette
              questions={session.questions}
              responses={responses}
              currentIndex={currentQuestionIndex}
              onNavigate={setCurrentQuestionIndex}
            />
          </div>'''

new_sidebar = '''          {/* Right Sidebar: Palette & Tracker */}
          <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
            <QuestionPalette
              questions={session.questions}
              responses={responses}
              currentIndex={currentQuestionIndex}
              onNavigate={setCurrentQuestionIndex}
            />
            
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100 bg-slate-50/50">
                <h3 className="text-sm font-semibold text-slate-800">AI Proctoring Active</h3>
                <p className="text-xs text-slate-500 mt-1">Your webcam is being monitored by AI.</p>
              </div>
              <div className="p-4 flex justify-center bg-slate-900">
                <FaceTracker enabled={!!session} onEventDetected={handleAIEvent} />
              </div>
            </div>
          </div>'''

text = text.replace(old_sidebar, new_sidebar)

with open(r'frontend\app\exam\[id]\page.tsx', 'w') as f:
    f.write(text)
