import { apiClient } from "./apiClient";

export type QuestionType = "MCQ_SINGLE" | "MCQ_MULTI" | "SHORT_ANSWER" | "ESSAY";
export type ExamStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";
export type SessionStatus = "READY" | "IN_PROGRESS" | "SUBMITTED" | "EXPIRED";

export interface QuestionOption {
  id: string;
  text: string;
}

export interface QuestionCandidate {
  id: string;
  type: QuestionType;
  title: string;
  content_rich_text: string;
  options?: QuestionOption[];
  points: number;
  order_index: number;
}

export interface CandidateResponse {
  question_id: string;
  response_data: any;
  is_flagged: boolean;
  sequence_id: number;
  server_timestamp: string;
}

export interface SessionState {
  session_id: string;
  exam_id: string;
  exam_title: string;
  status: SessionStatus;
  started_at: string;
  server_end_time: string;
  remaining_seconds: number;
  is_expired: boolean;
  questions: QuestionCandidate[];
  responses: Record<string, CandidateResponse>;
  total_questions: number;
  answered_count: number;
  flagged_count: number;
}

export interface ExamSummary {
  id: string;
  title: string;
  description?: string;
  duration_minutes: number;
  start_window: string;
  end_window: string;
  late_entry_minutes: number;
  status: ExamStatus;
  total_questions: number;
  total_points: number;
}

export interface AnswerSavePayload {
  question_id: string;
  response_data: any;
  sequence_id: number;
  is_flagged?: boolean;
  client_timestamp?: string;
}

export interface AnswerSaveResult {
  status: string;
  question_id: string;
  sequence_id: number;
  server_timestamp: string;
}

export interface SubmitResult {
  status: string;
  submitted_at: string;
  session_id: string;
}

class ExamService {
  public async listExams(status?: string): Promise<ExamSummary[]> {
    const query = status ? `?status=${status}` : "";
    return apiClient.get<ExamSummary[]>(`/api/exams${query}`);
  }

  public async getExam(examId: string): Promise<ExamSummary & { assigned_questions: any[] }> {
    return apiClient.get<ExamSummary & { assigned_questions: any[] }>(`/api/exams/${examId}`);
  }

  public async enrollCandidate(examId: string, candidateIds: string[]): Promise<any> {
    return apiClient.post(`/api/exams/${examId}/enroll`, { candidate_ids: candidateIds });
  }

  public async startSession(examId: string): Promise<SessionState> {
    return apiClient.post<SessionState>("/api/exam/sessions/start", { exam_id: examId });
  }

  public async getSessionState(sessionId: string): Promise<SessionState> {
    return apiClient.get<SessionState>(`/api/exam/sessions/${sessionId}`);
  }

  public async saveAnswer(sessionId: string, payload: AnswerSavePayload): Promise<AnswerSaveResult> {
    return apiClient.post<AnswerSaveResult>(`/api/exam/sessions/${sessionId}/answers`, {
      ...payload,
      client_timestamp: payload.client_timestamp || new Date().toISOString(),
    });
  }

  public async submitSession(sessionId: string): Promise<SubmitResult> {
    return apiClient.post<SubmitResult>(`/api/exam/sessions/${sessionId}/submit`, { confirm: true });
  }
}

export const examService = new ExamService();
