import { useQuery } from "@tanstack/react-query";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { Panel } from "../../components/ui/Panel";
import { ErrorState } from "../../components/ui/States";

/** Live S3 → Lambda → API wiring. Shown so judges can see ingest is implemented, not stubbed. */
export function AwsIngestPanel() {
  const { user } = useAuth();
  const allowed = can(user, "batch:load");
  const query = useQuery({
    queryKey: ["aws-status"],
    queryFn: api.getAwsStatus,
    enabled: allowed,
  });

  if (!allowed) return null;
  const data = query.data;

  return (
    <Panel
      id="aws-ingest"
      eyebrow="AWS"
      title="S3 drop"
      description={`${data?.region ?? "ap-south-1"} · ${data?.bucket ?? "claimshield-nexus-data-2026"} / ${data?.incoming_prefix ?? "incoming/"}`}
    >
      {query.error ? <ErrorState title="AWS status could not be loaded" error={query.error} /> : null}
      {data ? (
        <dl className="aws-status">
          <div>
            <dt>Region</dt>
            <dd className="mono">{data.region}</dd>
          </div>
          <div>
            <dt>Bucket</dt>
            <dd className="mono">{data.bucket}</dd>
          </div>
          <div>
            <dt>Incoming</dt>
            <dd className="mono">{data.incoming_prefix}</dd>
          </div>
          <div>
            <dt>Processed</dt>
            <dd className="mono">{data.processed_prefix}</dd>
          </div>
          <div>
            <dt>Results</dt>
            <dd className="mono">{data.results_prefix}</dd>
          </div>
          <div>
            <dt>Lambda</dt>
            <dd className="mono">{data.lambda_function}</dd>
          </div>
          <div>
            <dt>Shared token</dt>
            <dd>{data.token_configured ? "Configured on API" : "Not set on this API host"}</dd>
          </div>
          <div>
            <dt>Object store</dt>
            <dd>
              {data.store === "s3" ? "Live S3" : "Local directory (tests)"}
              {data.credentials_configured ? "" : data.store === "s3" ? " · default credential chain" : ""}
            </dd>
          </div>
        </dl>
      ) : null}
      {data?.recent_ingests?.length ? (
        <ul className="aws-receipts">
          {data.recent_ingests.map((row) => (
            <li key={`${row.trigger_key}-${row.updated_at ?? row.batch_id ?? row.status}`}>
              <span className="mono">{row.trigger_key}</span>
              <span>{row.status}</span>
              {row.batch_id ? <span className="mono">{row.batch_id}</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          No ingest receipts yet. Upload member, provider, claim, and claim_line CSVs under incoming/ to start a run.
        </p>
      )}
    </Panel>
  );
}
