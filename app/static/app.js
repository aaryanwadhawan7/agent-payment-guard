const COLOR = { allow:"green", paid:"green", needs_approval:"amber", pending:"amber",
                block:"red", blocked:"red", rejected:"gray", processing:"blue" };
const usd = n => new Intl.NumberFormat("en-US", { style:"currency", currency:"USD" }).format(n);
const loginForm = document.getElementById("login-form");
const adminBar = document.getElementById("admin-bar");
const tokenBox = document.getElementById("token");
let isAdmin = false;

// textContent (not innerHTML) so text from an agent can never inject HTML
function pillRenderer(p) {
  const s = document.createElement("span");
  s.className = "pill " + (COLOR[p.value] || "gray");
  s.textContent = String(p.value || "").replace("_", " ");
  return s;
}

function actionRenderer(p) {
  const box = document.createElement("span");
  if (!p.data || p.data.status !== "pending") return box;
  if (!isAdmin) {
    box.className = "hint";
    box.textContent = "Sign in to approve";
    return box;
  }
  [["Approve", "approve", "approve"],
   ["Approve + trust vendor", "approve?trust=true", "approve"],
   ["Reject", "reject", "reject"]].forEach(([label, path, cls]) => {
    const b = document.createElement("button");
    b.className = "btn " + cls;
    b.textContent = label;
    b.onclick = () => act(p.data.id, path);
    box.appendChild(b);
  });
  return box;
}

async function act(id, path) {
  const r = await fetch(`/decisions/${id}/${path}`, { method: "POST" });   // the cookie is sent automatically
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    alert(e.detail || "Request failed");
    if (r.status === 401) refreshAuth();
  }
  load();
}

const gridApi = agGrid.createGrid(document.getElementById("grid"), {
  columnDefs: [
    { field: "id", width: 70 },
    { field: "time", width: 170, valueFormatter: p => new Date(p.value).toLocaleString() },
    { field: "vendor_name", headerName: "Vendor", width: 160 },
    { field: "payee_email", headerName: "Payee", flex: 1, minWidth: 220 },
    { field: "amount", width: 110, valueFormatter: p => usd(p.value) },
    { field: "verdict", width: 150, cellRenderer: pillRenderer },
    { field: "status", width: 120, cellRenderer: pillRenderer },
    { field: "reasons", flex: 1.4, minWidth: 260,
      valueFormatter: p => (p.value || []).join(" • "),
      tooltipValueGetter: p => (p.value || []).join("\n") },
    { colId: "actions", headerName: "Action", width: 330, sortable: false, filter: false,
      valueGetter: p => p.data && p.data.status, cellRenderer: actionRenderer }
  ],
  defaultColDef: { sortable: true, filter: true, resizable: true },
  rowHeight: 48,
  tooltipShowDelay: 300,
  getRowId: p => String(p.data.id)
});

function stat(rows, statuses) {
  const f = rows.filter(r => statuses.includes(r.status));
  return { n: f.length, sum: f.reduce((a, r) => a + Number(r.amount), 0) };
}
function setText(id, text) { document.getElementById(id).textContent = text; }

async function load() {
  const rows = await (await fetch("/decisions")).json();
  gridApi.setGridOption("rowData", rows);
  const paid = stat(rows, ["paid"]);
  const pend = stat(rows, ["pending", "processing"]);
  const bad = stat(rows, ["blocked", "rejected"]);
  setText("paid-n", paid.n);        setText("paid-m", usd(paid.sum));
  setText("pending-n", pend.n);     setText("pending-m", usd(pend.sum));
  setText("blocked-n", bad.n);      setText("blocked-m", usd(bad.sum));
  setText("protected-m", usd(bad.sum));
}

async function refreshAuth() {
  const r = await fetch("/auth/me");
  isAdmin = (await r.json()).admin;
  loginForm.hidden = isAdmin;
  adminBar.hidden = !isAdmin;
  gridApi.refreshCells({ columns: ["actions"], force: true });   // redraw the buttons
}

loginForm.onsubmit = async e => {
  e.preventDefault();
  const r = await fetch("/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: tokenBox.value })
  });
  tokenBox.value = "";
  if (!r.ok) alert("Wrong admin token");
  refreshAuth();
};

document.getElementById("logout").onclick = async () => {
  await fetch("/auth/logout", { method: "POST" });
  refreshAuth();
};

load();
refreshAuth();
setInterval(load, 3000);

const labBtn = document.getElementById("lab-run");
labBtn.onclick = async () => {
  labBtn.disabled = true;
  labBtn.textContent = "Agent is working…";
  const head = document.getElementById("lab-headline");
  try {
    const r = await fetch("/demo/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: document.getElementById("lab-scenario").value,
                             mode: document.getElementById("lab-mode").value })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Request failed");
    document.getElementById("lab-invoice").textContent = d.invoice;
    head.className = "lab-headline " + d.level;
    head.textContent = d.headline;
    document.getElementById("lab-agent").textContent =
      d.agent_request ? "Agent's payment request: " + JSON.stringify(d.agent_request) : "";
    document.getElementById("lab-reasons").textContent = (d.reasons || []).join(" • ");
  } catch (e) {
    document.getElementById("lab-invoice").textContent = "";
    head.className = "lab-headline warn";
    head.textContent = e.message;
  } finally {
    document.getElementById("lab-out").hidden = false;
    labBtn.disabled = false;
    labBtn.textContent = "Run agent";
    load();
  }
};