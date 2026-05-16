import React, { useState, useEffect } from "react";
import { api, AuditEvent } from "../lib/api";
import LoadingCard from "./LoadingCard";
import EmptyState from "./EmptyState";

const AuditLogViewer: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAuditEvents(50)
      .then((res) => {
        setEvents(res.events);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <LoadingCard />;
  if (error) return <EmptyState title="Error" message={error} />;
  if (events.length === 0) return <EmptyState title="No Events" message="No audit events found." />;

  return (
    <div className="panel audit-log">
      <h3>Audit Log</h3>
      <ul className="audit-list">
        {events.map((e) => (
          <li key={e.event_id} className="audit-item">
            <span className="audit-type">{e.event_type}</span>
            <span className="audit-time">{new Date(e.timestamp).toLocaleString()}</span>
            {e.details && (
              <pre className="audit-details">{JSON.stringify(e.details, null, 2)}</pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AuditLogViewer;
