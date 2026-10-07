// All calls go to /api/... on the same origin; nginx (or the Vite proxy) forwards them to the backend.
async function request(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* non-JSON error body */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  listTickets: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request(`/api/tickets${q ? `?${q}` : ""}`);
  },
  stats: () => request("/api/tickets/stats"),
  createTicket: (data) => request("/api/tickets", { method: "POST", body: JSON.stringify(data) }),
  updateTicket: (id, data) => request(`/api/tickets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTicket: (id) => request(`/api/tickets/${id}`, { method: "DELETE" }),
};
