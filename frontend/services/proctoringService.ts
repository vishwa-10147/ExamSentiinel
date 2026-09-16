import { apiClient } from "./apiClient";

export type ProctoringEventType =
  | "TAB_BLUR"
  | "TAB_FOCUS"
  | "FULLSCREEN_EXIT"
  | "PASTE_ATTEMPT"
  | "COPY_ATTEMPT"
  | "RIGHT_CLICK"
  | "RESIZE"
  | "NETWORK_DISCONNECT"
  | "NETWORK_RECONNECT";

export interface ProctoringEventResult {
  session_id: string;
  event_type?: string;
  current_risk_score: number;
  risk_level: string;
  total_events: number;
}

class ProctoringService {
  public submitEvent(
    sessionId: string,
    eventType: ProctoringEventType,
    details: Record<string, unknown> = {}
  ): Promise<ProctoringEventResult> {
    return apiClient.post<ProctoringEventResult>("/api/telemetry/events", {
      session_id: sessionId,
      event_type: eventType,
      details,
      client_timestamp: new Date().toISOString(),
    });
  }
}

export const proctoringService = new ProctoringService();