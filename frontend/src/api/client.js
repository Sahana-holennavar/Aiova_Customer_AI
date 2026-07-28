import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

// ── Chat (primary interface) ────────────────────────────────────────────────

export const chatMessage = (message, complaintId = null) => {
  const form = new FormData();
  form.append("message", message);
  if (complaintId) form.append("complaint_id", complaintId);
  return api.post("/ai/chat", form);
};

export const chatUpload = (file, message = "", complaintId = null) => {
  const form = new FormData();
  form.append("file", file);
  if (message) form.append("message", message);
  if (complaintId) form.append("complaint_id", complaintId);
  return api.post("/ai/chat-upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// ── Legacy pipeline endpoints ───────────────────────────────────────────────

export const analyzeText = (text, sourceChannel = "manual") => {
  const form = new FormData();
  form.append("text", text);
  form.append("source_channel", sourceChannel);
  return api.post("/ai/analyze-text", form);
};

export const analyzeUpload = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/ai/analyze-upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const reanalyzeComplaint = (id) => api.post(`/ai/reanalyze/${id}`);

// ── CRUD ────────────────────────────────────────────────────────────────────

export const listComplaints = () => api.get("/complaints");
export const getComplaint = (id) => api.get(`/complaints/${id}`);
export const createComplaint = (payload) => api.post("/complaints", payload);
export const updateComplaint = (id, payload) => api.put(`/complaints/${id}`, payload);
export const deleteComplaint = (id) => api.delete(`/complaints/${id}`);

export default api;
