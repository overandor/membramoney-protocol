import React, { useState } from "react";

const PROGRAM_ID = "EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw";
const EXPLORER_URL = `https://explorer.solana.com/address/${PROGRAM_ID}?cluster=devnet`;

const DevnetBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) {
    return (
      <button
        className="banner-minimized"
        onClick={() => setDismissed(false)}
        aria-label="Show devnet warning"
        title="Devnet warning dismissed — click to show"
      >
        DEVNET
      </button>
    );
  }

  return (
    <div className="banner" role="alert">
      <span className="banner-text">
        <strong>EXPERIMENTAL DEVNET ONLY</strong> — NOT REAL MONEY —
        <a
          href={EXPLORER_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="banner-link"
        >
          View on Explorer
        </a>
      </span>
      <button
        className="banner-dismiss"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss devnet warning"
      >
        ×
      </button>
    </div>
  );
};

export default DevnetBanner;
