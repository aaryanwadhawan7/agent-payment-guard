const COLOR = { allow:"green", paid:"green", needs_approval:"amber", pending:"amber",
                block:"red", blocked:"red", rejected:"gray", processing:"blue" };
const usd = n => new Intl.NumberFormat("en-US", { style:"currency", currency:"USD" }).format(n);
const tokenBox = document.getElementById("token");
tokenBox.value = sessionStorage.getItem("adminToken") || "";
tokenBox.oninput = () => sessionStorage.setItem("adminToken", tokenBox.value);

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
  [["Approve", "approve"], ["Reject", "reject"]].forEach(([label, action]) => {
    const b = document.createElement("button");
    b.className = "btn " + action;
    b.textContent = label;
    b.onclick = () => act(p.data.id, action);
    box.appendChild(b);
  });
  return box;
}

async function act(id, action) {
  const r = await fetch(`/decisions/${id}/${action}`, {
    method: "POST", headers: { "X-Admin-Token": tokenBox.value }
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    alert(e.detail || "Request failed");
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
    { colId: "actions", headerName: "Action", width: 190, sortable: false, filter: false,
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

load();
setInterval(load, 3000);