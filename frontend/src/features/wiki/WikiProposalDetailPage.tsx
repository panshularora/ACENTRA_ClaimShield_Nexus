import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { api, ApiError, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { ProposalCard } from "./ProposalCard";

export function WikiProposalDetailPage() {
  const { proposalId } = useParams({ from: "/wiki/proposals/$proposalId" });
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const allowed = can(user, "wiki:read");
  const canApprove = can(user, "wiki:approve");

  const query = useQuery({
    queryKey: ["wiki-proposal", proposalId],
    queryFn: () => api.getProposal(proposalId),
    enabled: allowed,
  });

  const approveMut = useMutation({
    mutationFn: () => api.approveProposal(proposalId, note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposal", proposalId] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
    },
  });
  const rejectMut = useMutation({
    mutationFn: () => api.rejectProposal(proposalId, note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposal", proposalId] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
    },
  });

  if (!user) return null;
  if (!allowed) {
    return (
      <main id="main" className="page">
        <h1>Precedent proposal</h1>
        <p className="error-text">Your role cannot read wiki proposals.</p>
      </main>
    );
  }

  const proposal = query.data;
  const pending = proposal?.status === "pending";
  const error =
    approveMut.error instanceof ApiError
      ? approveMut.error.message
      : rejectMut.error instanceof ApiError
        ? rejectMut.error.message
        : approveMut.error
          ? (approveMut.error as Error).message
          : rejectMut.error
            ? (rejectMut.error as Error).message
            : null;

  return (
    <main id="main" className="page proposal-page">
      <header className="page-head">
        <div>
          <p className="kicker">Approval workflow</p>
          <h1 className="mono">{proposalId}</h1>
        </div>
        <Link to="/wiki/proposals" className="btn ghost">
          All proposals
        </Link>
      </header>
      {query.isLoading && <p className="muted">Loading proposal…</p>}
      {query.error && <p className="error-text">{(query.error as Error).message}</p>}
      {proposal && <ProposalCard proposal={proposal} />}
      {proposal && pending && (
        <section className="ws-panel review-panel">
          <h2>Manager / analyst review</h2>
          {!canApprove && (
            <p className="error-text">Your role cannot approve or reject precedents.</p>
          )}
          <label>
            Review note
            <textarea
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={!canApprove || approveMut.isPending || rejectMut.isPending}
              placeholder="Required for reject (20+ characters). Optional for approve."
            />
            <span className="muted mono">{note.trim().length}/20 for reject</span>
          </label>
          <div className="toolbar">
            <button
              type="button"
              className="btn solid"
              disabled={!canApprove || approveMut.isPending}
              onClick={() => approveMut.mutate()}
            >
              {approveMut.isPending ? "Approving…" : "Approve"}
            </button>
            <button
              type="button"
              className="btn"
              disabled={!canApprove || note.trim().length < 20 || rejectMut.isPending}
              onClick={() => rejectMut.mutate()}
            >
              {rejectMut.isPending ? "Rejecting…" : "Reject"}
            </button>
          </div>
          {error && <p className="error-text">{error}</p>}
        </section>
      )}
      {proposal && !pending && (
        <p className="muted">
          Reviewed {proposal.reviewed_at ?? ""} {proposal.review_note ? `· ${proposal.review_note}` : ""}
        </p>
      )}
    </main>
  );
}
