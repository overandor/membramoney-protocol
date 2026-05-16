import React from "react";

interface Props {
  lines?: number;
}

/**
 * Skeleton loading card — used while data is being fetched.
 */
const LoadingCard: React.FC<Props> = ({ lines = 4 }) => {
  return (
    <div className="panel loading-card" aria-busy="true" aria-label="Loading">
      <div className="skeleton skeleton-title" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton skeleton-line" style={{ width: `${70 + Math.random() * 30}%` }} />
      ))}
      <div className="skeleton skeleton-button" />
    </div>
  );
};

export default LoadingCard;
