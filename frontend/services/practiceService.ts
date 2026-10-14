import { apiClient } from "./apiClient";

export type Difficulty = "EASY" | "MEDIUM" | "HARD";
export type ProblemStatus = "solved" | "attempted" | "todo";
export type PracticeLanguage = "python" | "javascript" | "java" | "cpp" | "c" | "sql";
export type JudgeMode = "FUNCTION" | "STDIO" | "SQL";
export type Verdict =
  | "ACCEPTED"
  | "WRONG_ANSWER"
  | "TIME_LIMIT_EXCEEDED"
  | "MEMORY_LIMIT_EXCEEDED"
  | "OUTPUT_LIMIT_EXCEEDED"
  | "RUNTIME_ERROR"
  | "COMPILE_ERROR"
  | "SYSTEM_ERROR";

export interface FunctionSpec {
  name: string;
  params: { name: string; type: string; internal?: boolean }[];
  return_type: string;
  cycle?: { list: string; pos: string } | null;
}

export interface ProblemListItem {
  id: string;
  number: number | null;
  topic: string | null;
  slug: string;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  acceptance_rate: number | null;
  status: ProblemStatus;
}

export interface ExampleCase {
  input: string;
  expected_output: string;
  explanation: string | null;
}

export interface ProblemDetail {
  id: string;
  number: number | null;
  topic: string | null;
  slug: string;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  statement: string;
  input_format: string | null;
  output_format: string | null;
  constraints: string | null;
  complexity: string | null;
  /** Only present once the problem is solved (or for admins). */
  editorial: string | null;
  has_editorial: boolean;
  hints: string[];
  judge_mode: JudgeMode;
  function_spec: FunctionSpec | null;
  sql_schema: string | null;
  compare_mode: string;
  examples: ExampleCase[];
  starter_code: Record<string, string>;
  languages: PracticeLanguage[];
  time_limit_ms: number;
  memory_limit_mb: number;
  status: ProblemStatus;
  has_reference_solution: boolean;
}

export interface CaseResult {
  index: number;
  passed: boolean | null;
  input: string | null;
  expected: string | null;
  output: string | null;
  stdout: string;
  runtime_ms: number | null;
  error: string | null;
  is_custom: boolean;
}

export interface RunResult {
  verdict: Verdict;
  cases: CaseResult[];
  passed_count: number;
  total_count: number;
  runtime_ms: number | null;
  compile_output: string | null;
  error: string | null;
}

export interface Submission {
  id: string;
  problem_id: string;
  language: string;
  verdict: Verdict;
  passed_count: number;
  total_count: number;
  runtime_ms: number | null;
  failure: (Partial<CaseResult> & { case_number?: number; is_sample?: boolean }) | null;
  created_at: string;
  source_code?: string | null;
  compile_output?: string | null;
}

export interface PracticeStats {
  solved_total: number;
  problems_total: number;
  by_difficulty: Record<Difficulty, { solved: number; total: number }>;
  submissions_total: number;
  accepted_total: number;
  acceptance_rate: number | null;
  current_streak_days: number;
  activity: Record<string, number>;
  recent: { title: string; slug: string; verdict: Verdict; language: string; created_at: string }[];
  by_topic: TopicProgress[];
}

export interface TopicProgress {
  topic: string;
  solved: number;
  attempted: number;
  total: number;
}

export interface SubmissionHistoryItem {
  id: string;
  problem_number: number | null;
  problem_slug: string;
  problem_title: string;
  language: string;
  verdict: Verdict;
  passed_count: number;
  total_count: number;
  runtime_ms: number | null;
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  name: string;
  solved: number;
  easy: number;
  medium: number;
  hard: number;
}

// ---- Admin ----

export interface TestCaseInput {
  input_data: string;
  expected_output: string;
  is_sample: boolean;
  explanation?: string | null;
}

export interface ProblemUpsert {
  slug: string;
  number?: number | null;
  topic?: string | null;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  statement: string;
  input_format?: string | null;
  output_format?: string | null;
  constraints: string | null;
  complexity?: string | null;
  editorial?: string | null;
  hints: string[];
  judge_mode: JudgeMode;
  function_spec: FunctionSpec | null;
  sql_schema: string | null;
  compare_mode: "exact" | "unordered" | "float" | "checker";
  starter_code: Record<string, string>;
  reference_solution: { language: string; code: string } | null;
  time_limit_ms: number;
  memory_limit_mb: number;
  is_published: boolean;
  test_cases: TestCaseInput[];
}

export interface ProblemAdmin extends ProblemUpsert {
  id: string;
  test_cases: (TestCaseInput & { id: string; order_index: number })[];
  created_at: string;
  updated_at: string;
}

export interface ProblemAdminListItem {
  id: string;
  number: number | null;
  topic: string | null;
  slug: string;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  is_published: boolean;
  test_case_count: number;
  sample_count: number;
  submissions: number;
  acceptance_rate: number | null;
  suggested_difficulty: Difficulty | null;
  updated_at: string;
}

export interface ValidationReport {
  ok: boolean;
  verdict: Verdict;
  passed_count: number;
  total_count: number;
  message: string;
  failures: CaseResult[];
}

export const LANGUAGE_LABELS: Record<PracticeLanguage, string> = {
  python: "Python 3",
  javascript: "JavaScript",
  java: "Java",
  cpp: "C++17",
  c: "C",
  sql: "SQLite",
};

export const MONACO_LANGUAGE: Record<PracticeLanguage, string> = {
  python: "python",
  javascript: "javascript",
  java: "java",
  cpp: "cpp",
  c: "c",
  sql: "sql",
};

export const VERDICT_LABELS: Record<Verdict, string> = {
  ACCEPTED: "Accepted",
  WRONG_ANSWER: "Wrong Answer",
  TIME_LIMIT_EXCEEDED: "Time Limit Exceeded",
  MEMORY_LIMIT_EXCEEDED: "Memory Limit Exceeded",
  OUTPUT_LIMIT_EXCEEDED: "Output Limit Exceeded",
  RUNTIME_ERROR: "Runtime Error",
  COMPILE_ERROR: "Compile Error",
  SYSTEM_ERROR: "System Error",
};

class PracticeService {
  listProblems(params: { difficulty?: string; tag?: string; topic?: string; search?: string; status?: string; sort?: string } = {}) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && q.set(k, v));
    const qs = q.toString();
    return apiClient.get<{ items: ProblemListItem[]; total: number }>(`/api/practice/problems${qs ? `?${qs}` : ""}`);
  }
  listTags() {
    return apiClient.get<string[]>("/api/practice/tags");
  }
  listTopics() {
    return apiClient.get<TopicProgress[]>("/api/practice/topics");
  }
  history(params: { verdict?: string; limit?: number; offset?: number } = {}) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
    const qs = q.toString();
    return apiClient.get<{ items: SubmissionHistoryItem[]; total: number }>(`/api/practice/submissions${qs ? `?${qs}` : ""}`);
  }
  getProblem(slug: string) {
    return apiClient.get<ProblemDetail>(`/api/practice/problems/${encodeURIComponent(slug)}`);
  }
  run(slug: string, language: PracticeLanguage, code: string, customInput?: string) {
    return apiClient.post<RunResult>(`/api/practice/problems/${encodeURIComponent(slug)}/run`, {
      language,
      code,
      custom_input: customInput || null,
    });
  }
  submit(slug: string, language: PracticeLanguage, code: string) {
    return apiClient.post<Submission>(`/api/practice/problems/${encodeURIComponent(slug)}/submit`, { language, code });
  }
  submissions(slug: string) {
    return apiClient.get<Submission[]>(`/api/practice/problems/${encodeURIComponent(slug)}/submissions`);
  }
  stats() {
    return apiClient.get<PracticeStats>("/api/practice/stats/me");
  }
  leaderboard(limit = 10) {
    return apiClient.get<LeaderboardEntry[]>(`/api/practice/leaderboard?limit=${limit}`);
  }

  // Admin
  adminList() {
    return apiClient.get<ProblemAdminListItem[]>("/api/practice/admin/problems");
  }
  adminGet(id: string) {
    return apiClient.get<ProblemAdmin>(`/api/practice/admin/problems/${id}`);
  }
  adminCreate(payload: ProblemUpsert) {
    return apiClient.post<ProblemAdmin>("/api/practice/admin/problems", payload);
  }
  adminUpdate(id: string, payload: ProblemUpsert) {
    return apiClient.put<ProblemAdmin>(`/api/practice/admin/problems/${id}`, payload);
  }
  adminDelete(id: string) {
    return apiClient.delete<void>(`/api/practice/admin/problems/${id}`);
  }
  adminAddToExam(id: string, examId: string | null, points: number) {
    return apiClient.post<{ question_id: string; exam_id: string | null; title: string }>(
      `/api/practice/admin/problems/${id}/to-exam`,
      { exam_id: examId, points }
    );
  }
  adminValidate(id: string) {
    return apiClient.post<ValidationReport>(`/api/practice/admin/problems/${id}/validate`, {});
  }
}

export const practiceService = new PracticeService();

/** "nums = [2,7]" style lines for FUNCTION-mode inputs; raw text for STDIO. */
export function formatCaseInput(input: string | null, spec: FunctionSpec | null): string {
  if (input == null) return "";
  if (!spec) return input;
  const lines = input.split("\n");
  return spec.params.map((p, i) => `${p.name} = ${lines[i] ?? ""}`).join("\n");
}
