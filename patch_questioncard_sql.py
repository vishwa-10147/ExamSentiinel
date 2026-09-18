import sys
import re

with open(r'frontend\components\exam\QuestionCard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

sql_block = '''
          {question.type === "SQL" && (
            <div className="border border-slate-700 rounded-lg overflow-hidden flex flex-col h-[600px] mb-4">
              <div className="flex items-center justify-between bg-slate-800 px-4 py-2 border-b border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    SQL Editor (SQLite)
                  </span>
                </div>
                <button 
                  onClick={() => {
                     const old = activeLang;
                     setActiveLang("sql");
                     runCode().then(() => setActiveLang(old));
                  }}
                  disabled={isExecuting}
                  className="px-3 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40 rounded text-xs font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
                >
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> 
                  {isExecuting ? "Executing..." : "Run Query"}
                </button>
              </div>
              
              {/* Schema Viewer */}
              {(question as any).database_schema && (
                <div className="bg-slate-900 border-b border-slate-700 p-3 overflow-x-auto text-xs text-slate-400 font-mono">
                  <div className="text-[10px] uppercase text-slate-500 mb-1 font-bold">Database Schema</div>
                  <pre>{(question as any).database_schema}</pre>
                </div>
              )}

              <div className="w-full h-[350px] md:h-[500px] border-b border-slate-700">
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language="sql"
                  value={responseData?.text || "-- Write your SQL query here\\n"}
                  onChange={(val) => onAnswerChange({ text: val || "" })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineHeight: 24,
                    padding: { top: 16, bottom: 16 },
                  }}
                />
              </div>
              {/* Output Panel */}
              <div className="h-48 border-t border-slate-700 bg-slate-900 text-slate-300 font-mono text-sm overflow-y-auto p-4 flex flex-col">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-semibold">Query Result</div>
                {output.length > 0 ? (
                  output.map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap">{line}</div>
                  ))
                ) : (
                  <div className="text-slate-600 italic">No output yet. Click 'Run Query' to execute.</div>
                )}
              </div>
            </div>
          )}
'''

text = re.sub(
    r'(\s*\{question\.type === "CODING" && \()',
    sql_block + r'\n\1',
    text,
    count=1
)

with open(r'frontend\components\exam\QuestionCard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
