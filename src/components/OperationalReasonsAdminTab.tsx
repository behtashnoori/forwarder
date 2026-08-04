import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createExecutionReason, listExecutionReasons, updateExecutionReason, type ExecutionReason } from "@/lib/api";

export default function OperationalReasonsAdminTab() {
  const [kind, setKind] = useState<"delay" | "exception">("delay");
  const [rows, setRows] = useState<ExecutionReason[]>([]);
  const [form, setForm] = useState({ immutable_code: "", fa_name: "", en_name: "", definition: "" });
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try { setRows((await listExecutionReasons(kind)).data); setError(""); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load reasons"); }
  }, [kind]);
  useEffect(() => { void load(); }, [load]);
  const create = async () => {
    try { await createExecutionReason(kind, form); setForm({ immutable_code: "", fa_name: "", en_name: "", definition: "" }); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create reason"); }
  };
  return <div className="space-y-4">
    <div className="flex gap-2"><Button variant={kind === "delay" ? "default" : "outline"} onClick={() => setKind("delay")}>Delay reasons</Button><Button variant={kind === "exception" ? "default" : "outline"} onClick={() => setKind("exception")}>Exception reasons</Button></div>
    {error && <p role="alert">{error}</p>}
    <div className="grid gap-2 md:grid-cols-4"><Input aria-label="Immutable code" placeholder="Immutable code" value={form.immutable_code} onChange={event => setForm({ ...form, immutable_code: event.target.value })}/><Input aria-label="Persian name" placeholder="Persian name" value={form.fa_name} onChange={event => setForm({ ...form, fa_name: event.target.value })}/><Input aria-label="English name" placeholder="English name" value={form.en_name} onChange={event => setForm({ ...form, en_name: event.target.value })}/><Button disabled={!form.immutable_code || !form.fa_name || !form.en_name} onClick={() => void create()}>Create reason</Button></div>
    {!rows.length && <p>No reasons exist. Create the first governed reason above; deployment does not seed this catalog.</p>}
    <div className="grid gap-3 md:grid-cols-2">{rows.map(row => <article className="rounded border p-3" key={row.public_id}><strong>{row.immutable_code} · {row.fa_name} / {row.en_name}</strong><p>{row.definition || "No definition"}</p><Button variant="outline" onClick={() => void updateExecutionReason(kind, row, { is_active: !row.is_active }).then(load)}>{row.is_active ? "Deactivate" : "Activate"}</Button></article>)}</div>
  </div>;
}
