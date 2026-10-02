"use client";

import * as React from "react";
import { Search, User, Beaker, Loader2, AlertTriangle, RotateCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getPatientDetail, getTrialDetail } from "@/lib/api";
import { truncate } from "@/lib/utils";
import type { Patient, Trial } from "@/types/clinical";

const PAGE_SIZE = 10;

function usePagination<T>(items: T[]) {
  const [page, setPage] = React.useState(0);
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages - 1);
  const pageItems = items.slice(clampedPage * PAGE_SIZE, clampedPage * PAGE_SIZE + PAGE_SIZE);
  React.useEffect(() => setPage(0), [items.length]);
  return { page: clampedPage, setPage, totalPages, pageItems };
}

function PreviewDrawer({
  open,
  onOpenChange,
  kind,
  id,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  kind: "patient" | "trial";
  id: string | null;
}) {
  const [content, setContent] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open || !id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setContent(null);
    const fetcher = kind === "patient" ? getPatientDetail(id) : getTrialDetail(id);
    fetcher
      .then((res) => {
        if (!cancelled) setContent("content" in res ? res.content : "");
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load record.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, id, kind]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="font-mono">{id}</DialogTitle>
          <DialogDescription>
            {kind === "patient" ? "Full EHR record" : "Full protocol criteria"} · GET /api/
            {kind === "patient" ? "patients" : "trials"}/{id}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] px-6 py-4">
          {loading && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/6" />
            </div>
          )}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-rose-600/30 bg-rose-500/[0.06] px-4 py-3 text-sm text-rose-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          {content && (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">{content}</pre>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function PatientTable({ patients, loading, query }: { patients: Patient[]; loading: boolean; query: string }) {
  const filtered = React.useMemo(
    () =>
      patients.filter(
        (p) =>
          p.patient_id.toLowerCase().includes(query.toLowerCase()) ||
          p.preview.toLowerCase().includes(query.toLowerCase()),
      ),
    [patients, query],
  );
  const { page, setPage, totalPages, pageItems } = usePagination(filtered);
  const [previewId, setPreviewId] = React.useState<string | null>(null);

  if (loading) {
    return (
      <div className="flex flex-col gap-2 p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-56">Patient ID</TableHead>
            <TableHead>Clinical Snippet</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageItems.map((p) => (
            <TableRow key={p.patient_id} className="cursor-pointer" onClick={() => setPreviewId(p.patient_id)}>
              <TableCell className="font-mono text-xs font-medium text-teal-400">{p.patient_id}</TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {truncate(p.preview.replace(/\n/g, " "), 130)}
              </TableCell>
            </TableRow>
          ))}
          {pageItems.length === 0 && (
            <TableRow>
              <TableCell colSpan={2} className="py-10 text-center text-sm text-muted-foreground">
                No patients match your search.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <PaginationBar page={page} totalPages={totalPages} onChange={setPage} total={filtered.length} />
      <PreviewDrawer open={previewId !== null} onOpenChange={(v) => !v && setPreviewId(null)} kind="patient" id={previewId} />
    </>
  );
}

function TrialTable({ trials, loading, query }: { trials: Trial[]; loading: boolean; query: string }) {
  const filtered = React.useMemo(
    () =>
      trials.filter(
        (t) =>
          t.trial_id.toLowerCase().includes(query.toLowerCase()) ||
          t.preview.toLowerCase().includes(query.toLowerCase()),
      ),
    [trials, query],
  );
  const { page, setPage, totalPages, pageItems } = usePagination(filtered);
  const [previewId, setPreviewId] = React.useState<string | null>(null);

  if (loading) {
    return (
      <div className="flex flex-col gap-2 p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-56">Trial ID</TableHead>
            <TableHead>Protocol Snippet</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageItems.map((t) => (
            <TableRow key={t.trial_id} className="cursor-pointer" onClick={() => setPreviewId(t.trial_id)}>
              <TableCell className="font-mono text-xs font-medium text-indigo-400">{t.trial_id}</TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {truncate(t.preview.replace(/\n/g, " "), 130)}
              </TableCell>
            </TableRow>
          ))}
          {pageItems.length === 0 && (
            <TableRow>
              <TableCell colSpan={2} className="py-10 text-center text-sm text-muted-foreground">
                No trials match your search.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <PaginationBar page={page} totalPages={totalPages} onChange={setPage} total={filtered.length} />
      <PreviewDrawer open={previewId !== null} onOpenChange={(v) => !v && setPreviewId(null)} kind="trial" id={previewId} />
    </>
  );
}

function PaginationBar({
  page,
  totalPages,
  onChange,
  total,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
  total: number;
}) {
  return (
    <div className="flex items-center justify-between border-t border-border px-4 py-3">
      <p className="text-xs text-muted-foreground">
        Page <span className="tabular font-medium text-foreground">{page + 1}</span> of{" "}
        <span className="tabular font-medium text-foreground">{totalPages}</span> · {total} records
      </p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page === 0} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}

export function CohortExplorer({
  patients,
  patientsLoading,
  patientsError,
  trials,
  trialsLoading,
  trialsError,
  onRefresh,
}: {
  patients: Patient[];
  patientsLoading: boolean;
  patientsError: string | null;
  trials: Trial[];
  trialsLoading: boolean;
  trialsError: string | null;
  onRefresh: () => void;
}) {
  const [query, setQuery] = React.useState("");

  return (
    <Card className="overflow-hidden">
      <Tabs defaultValue="patients">
        <div className="flex flex-col gap-4 border-b border-border p-5 sm:flex-row sm:items-center sm:justify-between">
          <TabsList>
            <TabsTrigger value="patients" className="gap-1.5">
              <User className="h-3.5 w-3.5" /> Patients
            </TabsTrigger>
            <TabsTrigger value="trials" className="gap-1.5">
              <Beaker className="h-3.5 w-3.5" /> Protocols
            </TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by ID or snippet…"
                className="w-64 pl-9"
              />
            </div>
            <Button variant="outline" size="icon" onClick={onRefresh} aria-label="Refresh">
              <RotateCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <TabsContent value="patients" className="mt-0">
          {patientsError ? (
            <ErrorState message={patientsError} onRetry={onRefresh} />
          ) : (
            <PatientTable patients={patients} loading={patientsLoading} query={query} />
          )}
        </TabsContent>
        <TabsContent value="trials" className="mt-0">
          {trialsError ? (
            <ErrorState message={trialsError} onRetry={onRefresh} />
          ) : (
            <TrialTable trials={trials} loading={trialsLoading} query={query} />
          )}
        </TabsContent>
      </Tabs>
    </Card>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <AlertTriangle className="h-6 w-6 text-rose-400" />
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <Loader2 className="hidden h-3.5 w-3.5 animate-spin" />
        Retry
      </Button>
    </div>
  );
}
