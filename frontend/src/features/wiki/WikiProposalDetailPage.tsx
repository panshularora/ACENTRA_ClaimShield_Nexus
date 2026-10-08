import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { ErrorState, LoadingState } from "../../components/ui/States";
import { dateTime } from "../../lib/format";
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
        <PageHeader eyebrow="Approval workflow" title="Precedent proposal" />
        <ErrorState title="Access denied" error="Your role cannot read wiki proposals." />
      </main>
    );
  }

  const proposal = query.data;
  const pending = proposal?.status === "pending";
  const busy = approveMut.isPending || rejectMut.isPending;
  const noteLength = note.trim().length;
  const mutationError = approveMut.error ?? rejectMut.error;

  return (
    <main id="main" className="page proposal-page">
      <PageHeader
        eyebrow="Approval workflow"
        title={proposal?.title ?? proposalId}
        description={<span className="mono">{proposalId}</span>}
        actions={
          <Link to="/wiki/proposals" className="btn ghost">
            All proposals
          </Link>
        }
      />
      {query.isLoading ? <LoadingState label="Loading proposal…" /> : null}
      {query.error ? <ErrorState title="Proposal unavailable" error={query.error} /> : null}
      {proposal ? (
        <div className="proposal-layout">
          <ProposalCard proposal={proposal} />
          {pending ? (
            <Panel id="review" eyebrow="Review" title="Manager or analyst decision" className="review-panel">
              {!canApprove ? <p className="banner info">Your role cannot approve or reject precedents.</p> : null}
              <label className="field">
                Review note
                <textarea
                  rows={4}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  disabled={!canApprove || busy}
                  aria-describedby="review-note-hint"
                  placeholder="Required to reject (20+ characters). Optional to approve."
                />
                <span id="review-note-hint" className="field-hint">
                  {noteLength}/20 characters needed to reject
                </span>
              </label>
              <div className="chip-row">
                <button
                  type="button"
                  className="btn solid"
                  disabled={!canApprove || busy}
                  onClick={() => approveMut.mutate()}
                >
                  {approveMut.isPending ? "Approving…" : "Approve and publish"}
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={!canApprove || noteLength < 20 || busy}
                  onClick={() => rejectMut.mutate()}
                >
                  {rejectMut.isPending ? "Rejecting…" : "Reject"}
                </button>
              </div>
              {mutationError ? <ErrorState title="Review not recorded" error={mutationError} /> : null}
            </Panel>
          ) : (
            <Panel id="review" eyebrow="Review" title="Reviewed" className="review-panel">
              <p>
                {proposal.reviewed_at ? <time dateTime={proposal.reviewed_at}>{dateTime(proposal.reviewed_at)}</time> : "Time not recorded"}
              </p>
              {proposal.review_note ? <p>{proposal.review_note}</p> : <p className="muted">No review note.</p>}
            </Panel>
          )}
        </div>
      ) : null}
    </main>
  );
}
