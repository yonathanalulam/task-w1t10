import { apiGet, apiPatch, apiPost } from "./client";

export type MessageTemplate = {
  id: string;
  project_id: string;
  name: string;
  category: string;
  channel: string;
  body_template: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type MessagePreview = {
  template_id: string;
  rendered_body: string;
  missing_variables: string[];
  variables_used: Record<string, string>;
};

export type MessageDeliveryAttempt = {
  id: string;
  connector_key: string;
  attempt_status: string;
  provider_message_id: string | null;
  detail: string | null;
  response_payload: Record<string, unknown> | null;
  attempted_at: string;
};

export type MessageDispatch = {
  id: string;
  project_id: string;
  itinerary_id: string | null;
  template_id: string | null;
  template_name: string;
  template_category: string;
  channel: string;
  recipient_user_id: string;
  recipient_display_name: string | null;
  rendered_body: string;
  send_status: string;
  variables_payload: Record<string, string>;
  created_by_user_id: string;
  created_at: string;
  attempts: MessageDeliveryAttempt[];
};

export const messageCenterApi = {
  listTemplates: (projectId: string) => apiGet<MessageTemplate[]>(`/api/projects/${projectId}/message-center/templates`),

  createTemplate: (
    projectId: string,
    payload: {
      name: string;
      category: string;
      channel: string;
      body_template: string;
      is_active: boolean;
    }
  ) => apiPost<MessageTemplate>(`/api/projects/${projectId}/message-center/templates`, payload),

  updateTemplate: (
    projectId: string,
    templateId: string,
    payload: {
      name?: string;
      category?: string;
      channel?: string;
      body_template?: string;
      is_active?: boolean;
    }
  ) => apiPatch<MessageTemplate>(`/api/projects/${projectId}/message-center/templates/${templateId}`, payload),

  preview: (
    projectId: string,
    payload: {
      template_id: string;
      itinerary_id?: string | null;
      variables: Record<string, string>;
    }
  ) => apiPost<MessagePreview>(`/api/projects/${projectId}/message-center/preview`, payload),

  send: (
    projectId: string,
    payload: {
      template_id: string;
      recipient_user_id: string;
      itinerary_id?: string | null;
      variables: Record<string, string>;
    }
  ) => apiPost<MessageDispatch>(`/api/projects/${projectId}/message-center/send`, payload),

  listTimeline: (projectId: string, limit = 50) =>
    apiGet<MessageDispatch[]>(`/api/projects/${projectId}/message-center/timeline?limit=${encodeURIComponent(String(limit))}`)
};
