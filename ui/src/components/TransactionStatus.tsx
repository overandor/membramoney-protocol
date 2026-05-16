import React from "react";

interface TransactionStatusProps {
  status: "pending" | "confirmed" | "failed";
  signature?: string;
  error?: string;
}

const TransactionStatus: React.FC<TransactionStatusProps> = ({ status, signature, error }) => {
  const statusConfig = {
    pending: { icon: "⏳", className: "status-pending", text: "Transaction pending..." },
    confirmed: { icon: "✅", className: "status-confirmed", text: "Transaction confirmed!" },
    failed: { icon: "❌", className: "status-failed", text: "Transaction failed" },
  };

  const config = statusConfig[status];

  return (
    <div className={`transaction-status ${config.className}`}>
      <span className="status-icon">{config.icon}</span>
      <span className="status-text">{config.text}</span>
      {signature && status === "confirmed" && (
        <a
          href={`https://explorer.solana.com/tx/${signature}?cluster=devnet`}
          target="_blank"
          rel="noopener noreferrer"
          className="explorer-link"
        >
          View on Explorer
        </a>
      )}
      {error && status === "failed" && (
        <span className="error-detail">{error}</span>
      )}
    </div>
  );
};

export default TransactionStatus;
