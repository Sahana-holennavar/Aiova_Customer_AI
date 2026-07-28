import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import * as api from "../../api/client";

// ── Async thunks ────────────────────────────────────────────────────────────

export const fetchComplaints = createAsyncThunk("complaints/fetchAll", async () => {
  const res = await api.listComplaints();
  return res.data;
});

export const sendChatMessage = createAsyncThunk(
  "complaints/sendChat",
  async ({ message, complaintId }) => {
    const res = await api.chatMessage(message, complaintId);
    return res.data;
  }
);

export const uploadChatFile = createAsyncThunk(
  "complaints/chatUpload",
  async ({ file, message, complaintId }) => {
    const res = await api.chatUpload(file, message, complaintId);
    return res.data;
  }
);

export const saveComplaintEdits = createAsyncThunk(
  "complaints/saveEdits",
  async ({ id, payload }) => {
    const res = await api.updateComplaint(id, payload);
    return res.data;
  }
);

// ── Slice ───────────────────────────────────────────────────────────────────

const complaintsSlice = createSlice({
  name: "complaints",
  initialState: {
    // Complaint data
    list: [],
    activeDraft: null,
    pipelineResult: null,
    activeComplaintId: null,
    // Chat state
    chatMessages: [],
    isTyping: false,
    // Generic
    status: "idle",
    error: null,
  },
  reducers: {
    updateDraftField(state, action) {
      const { field, value } = action.payload;
      if (state.activeDraft) state.activeDraft[field] = value;
    },
    clearDraft(state) {
      state.activeDraft = null;
      state.pipelineResult = null;
      state.activeComplaintId = null;
    },
    setActiveDraft(state, action) {
      state.activeDraft = action.payload;
    },
    setPipelineResult(state, action) {
      state.pipelineResult = action.payload;
    },
    clearChat(state) {
      state.chatMessages = [];
      state.activeComplaintId = null;
      state.activeDraft = null;
      state.pipelineResult = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // ── addCase handlers (MUST come before addMatcher) ──────────────
      .addCase(fetchComplaints.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.list = action.payload;
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message;
      })
      .addCase(saveComplaintEdits.fulfilled, (state, action) => {
        const idx = state.list.findIndex((c) => c.id === action.payload.id);
        if (idx >= 0) state.list[idx] = action.payload;
        state.activeDraft = { ...state.activeDraft, ...action.payload };
        state.error = null;
      })
      .addCase(saveComplaintEdits.rejected, (state, action) => {
        state.error = action.error?.message || "Failed to save complaint.";
      })
      // ── Chat: pending (add user message, show typing) ──────────────
      .addCase(sendChatMessage.pending, (state, action) => {
        state.chatMessages.push({
          role: "user",
          content: action.meta.arg.message,
        });
        state.isTyping = true;
        state.error = null;
      })
      .addCase(uploadChatFile.pending, (state, action) => {
        const fileName = action.meta.arg.file?.name || "file";
        state.chatMessages.push({
          role: "user",
          content: `[Uploaded: ${fileName}]${action.meta.arg.message ? " " + action.meta.arg.message : ""}`,
        });
        state.isTyping = true;
        state.error = null;
      })
      // ── Chat: fulfilled (add AI response, update form) ─────────────
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.isTyping = false;
        const data = action.payload;
        state.chatMessages.push({
          role: "assistant",
          content: data.response,
        });
        if (data.pipeline_result) {
          const pr = data.pipeline_result;
          state.pipelineResult = pr;
          state.activeDraft = {
            id: data.complaint_id,
            ...pr.extracted_fields,
            ai_severity: pr.risk?.severity,
            ai_risk_score: pr.risk?.risk_score,
            ai_risk_rationale: pr.risk?.rationale,
            ai_is_adverse_event: pr.risk?.is_adverse_event,
            ai_completeness_status: pr.completeness?.completeness_status,
            ai_missing_fields: pr.completeness?.missing_fields,
            ai_root_cause_suggestions: pr.root_cause?.root_cause_hypotheses,
            ai_capa_suggestions: pr.capa?.corrective_actions,
            ai_summary: pr.summary,
          };
          state.activeComplaintId = data.complaint_id;
        }
        state.status = "succeeded";
        state.error = null;
      })
      .addCase(uploadChatFile.fulfilled, (state, action) => {
        state.isTyping = false;
        const data = action.payload;
        state.chatMessages.push({
          role: "assistant",
          content: data.response,
        });
        if (data.pipeline_result) {
          const pr = data.pipeline_result;
          state.pipelineResult = pr;
          state.activeDraft = {
            id: data.complaint_id,
            ...pr.extracted_fields,
            ai_severity: pr.risk?.severity,
            ai_risk_score: pr.risk?.risk_score,
            ai_risk_rationale: pr.risk?.rationale,
            ai_is_adverse_event: pr.risk?.is_adverse_event,
            ai_completeness_status: pr.completeness?.completeness_status,
            ai_missing_fields: pr.completeness?.missing_fields,
            ai_root_cause_suggestions: pr.root_cause?.root_cause_hypotheses,
            ai_capa_suggestions: pr.capa?.corrective_actions,
            ai_summary: pr.summary,
          };
          state.activeComplaintId = data.complaint_id;
        }
        state.status = "succeeded";
        state.error = null;
      })
      // ── Chat: rejected ─────────────────────────────────────────────
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.isTyping = false;
        state.chatMessages.push({
          role: "assistant",
          content: "Sorry, something went wrong. Please check the backend server and try again.",
        });
        state.error = action.error?.message || "Chat request failed.";
      })
      .addCase(uploadChatFile.rejected, (state, action) => {
        state.isTyping = false;
        state.chatMessages.push({
          role: "assistant",
          content: "Sorry, the file upload failed. Please try again.",
        });
        state.error = action.error?.message || "Upload failed.";
      });
  },
});

export const { updateDraftField, clearDraft, setActiveDraft, setPipelineResult, clearChat } =
  complaintsSlice.actions;
export default complaintsSlice.reducer;
