import React from "react";

type Props = {
  children: React.ReactNode;
  fallback?: React.ReactNode;
};

type State = { hasError: boolean; error?: any };

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: any): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, info: any) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div style={{
          padding: 16,
          border: "1px solid #fee2e2",
          background: "#fef2f2",
          color: "#991b1b",
          borderRadius: 12
        }}>
          <strong>Something went wrong.</strong>
          <div style={{ marginTop: 6, fontSize: 12 }}>{String(this.state.error)}</div>
        </div>
      );
    }
    return this.props.children;
  }
}
