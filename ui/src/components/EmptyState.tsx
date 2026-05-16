import React from "react";

interface Props {
  title: string;
  description?: string;
  message?: string;
  icon?: string;
}

/**
 * Empty state component — shown when there is no data to display.
 */
const EmptyState: React.FC<Props> = ({ title, description, message, icon = "∅" }) => {
  const desc = description || message;
  return (
    <div className="empty-state" role="status">
      <span className="empty-state-icon">{icon}</span>
      <h3 className="empty-state-title">{title}</h3>
      {desc && <p className="empty-state-desc">{desc}</p>}
    </div>
  );
};

export default EmptyState;
