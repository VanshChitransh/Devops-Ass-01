import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const STATUSES = ["open", "in_progress", "resolved", "closed"];
const PRIORITIES = ["low", "medium", "high", "urgent"];
const NEXT = { open: "in_progress", in_progress: "resolved", resolved: "closed" };
const label = (s) => s.replace("_", " ");
const ago = (iso) => {
  const m = Math.round((Date.now() - new Date(iso)) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
};

const EMPTY = { title: "", description: "", priority: "medium", requester: "", assignee: "" };

export default function App() {
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({ status: "", priority: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const [t, s] = await Promise.all([api.listTickets(filters), api.stats()]);
      setTickets(t);
      setStats(s);
    } catch (e) {
      setError(`Backend unavailable: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.createTicket(form);
      setForm(EMPTY);
      setShowModal(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const advance = async (t) => { if (NEXT[t.status]) { await api.updateTicket(t.id, { status: NEXT[t.status] }); load(); } };
  const assignMe = async (t) => { await api.updateTicket(t.id, { assignee: "vansh" }); load(); };
  const remove = async (t) => { if (confirm(`Delete ticket #${t.id}?`)) { await api.deleteTicket(t.id); load(); } };

  const recent = [...tickets].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 6);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand"><span className="logo">TH</span><div><strong>TicketHub</strong><small>Vansh's helpdesk</small></div></div>
        <nav>
          <a className="active" href="#">Dashboard</a>
          <a href="#tickets">Tickets</a>
          <a href="/docs" target="_blank" rel="noreferrer">API docs</a>
          <a href="/metrics" target="_blank" rel="noreferrer">Metrics</a>
        </nav>
        <div className="pipeline">
          <small>Delivery pipeline</small>
          {["tests", "scan", "build", "push", "deploy"].map((s) => <span key={s} className="step">{s}</span>)}
        </div>
        <footer>DevOps capstone, SST</footer>
      </aside>

      <main>
        <header className="topbar">
          <div><h1>Support dashboard</h1><p>Every ticket in one place: create, triage, assign, resolve.</p></div>
          <button className="primary" onClick={() => setShowModal(true)}>+ New ticket</button>
        </header>

        {error && <div className="banner error">{error} <button onClick={load}>retry</button></div>}

        <section className="kpis">
          <Kpi label="Total tickets" value={stats?.total} />
          <Kpi label="Open" value={stats?.by_status.open} tone="blue" />
          <Kpi label="In progress" value={stats?.by_status.in_progress} tone="amber" />
          <Kpi label="Urgent, unresolved" value={stats?.open_urgent} tone="red" />
          <Kpi label="Unassigned" value={stats?.unassigned} tone="grey" />
        </section>

        <section className="content">
          <div className="card table-card" id="tickets">
            <div className="card-head">
              <h2>Tickets</h2>
              <div className="filters">
                <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                  <option value="">All statuses</option>
                  {STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
                </select>
                <select value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
                  <option value="">All priorities</option>
                  {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            {loading ? <p className="muted">Loading tickets...</p> : tickets.length === 0 ? (
              <p className="muted">No tickets match. Create the first one.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>#</th><th>Title</th><th>Priority</th><th>Status</th><th>Requester</th><th>Assignee</th><th>Updated</th><th></th></tr></thead>
                  <tbody>
                    {tickets.map((t) => (
                      <tr key={t.id}>
                        <td className="muted">{t.id}</td>
                        <td><strong>{t.title}</strong>{t.description && <div className="desc">{t.description}</div>}</td>
                        <td><span className={`badge p-${t.priority}`}>{t.priority}</span></td>
                        <td><span className={`badge s-${t.status}`}>{label(t.status)}</span></td>
                        <td>{t.requester}</td>
                        <td>{t.assignee || <em className="muted">unassigned</em>}</td>
                        <td className="muted">{ago(t.updated_at)}</td>
                        <td className="actions">
                          {!t.assignee && <button onClick={() => assignMe(t)}>assign me</button>}
                          {NEXT[t.status] && <button onClick={() => advance(t)}>{label(NEXT[t.status])}</button>}
                          <button className="danger" onClick={() => remove(t)}>delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card feed">
            <h2>Recent activity</h2>
            {recent.length === 0 ? <p className="muted">Nothing yet.</p> : (
              <ul>
                {recent.map((t) => (
                  <li key={t.id}><span className={`dot s-${t.status}`} /><div><strong>#{t.id} {t.title}</strong><small>{label(t.status)} by {t.assignee || t.requester}, {ago(t.updated_at)}</small></div></li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>

      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
            <h2>New ticket</h2>
            <label>Title<input required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            <label>Description<textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
            <div className="row">
              <label>Priority<select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</select></label>
              <label>Requester<input required value={form.requester} onChange={(e) => setForm({ ...form, requester: e.target.value })} placeholder="name or email" /></label>
            </div>
            <label>Assignee (optional)<input value={form.assignee} onChange={(e) => setForm({ ...form, assignee: e.target.value })} /></label>
            <div className="modal-actions">
              <button type="button" onClick={() => setShowModal(false)}>Cancel</button>
              <button type="submit" className="primary" disabled={saving}>{saving ? "Saving..." : "Create ticket"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, tone = "" }) {
  return <div className={`kpi ${tone}`}><small>{label}</small><strong>{value ?? "–"}</strong></div>;
}
