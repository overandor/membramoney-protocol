import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * Error Boundary — catches React render errors and displays a devnet-safe fallback.
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // In production this would report to Sentry / error aggregator
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-fallback panel" role="alert">
          <h2 className="error-title">Something went wrong</h2>
          <p className="error-message">
            The UI encountered an unexpected error. This is a devnet preview —
            no real funds are at risk.
          </p>
          {this.state.error && (
            <pre className="error-details">
              {this.state.error.toString()}
            </pre>
          )}
          <button
            className="btn-primary"
            onClick={() => window.location.reload()}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
