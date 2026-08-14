import { Component, createRef, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  key: number;
}

// Catches render-time crashes and remounts the whole subtree instead of
// leaving React's torn-down (blank) DOM on screen. The main trigger in
// practice: the browser's own page-translate feature rewrites text nodes
// in place, and the next unrelated re-render (a query refetch, a route
// change) makes React try to remove/patch DOM it no longer recognizes —
// throwing "Failed to execute 'removeChild' on 'Node'" mid-commit.
//
// That exception fires *during* React's DOM mutation pass, so React's own
// bookkeeping can be left inconsistent with the real DOM: nodes that were
// supposed to be deleted as part of the same commit can survive, sitting
// orphaned next to whatever remounts next (confirmed by deliberately
// reproducing this locally — a plain key-remount left the old and new
// trees rendered side by side instead of the old one disappearing). So
// recovery can't just trust React to clean up — the wrapper's real DOM is
// wiped by hand first, then React remounts into a genuinely empty node.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, key: 0 };
  private ref = createRef<HTMLDivElement>();

  static getDerivedStateFromError(): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Render crashed, remounting:", error, info.componentStack);
    if (this.ref.current) this.ref.current.innerHTML = "";
    // Defer past this failed commit before mounting fresh children.
    setTimeout(() => {
      this.setState((s) => ({ hasError: false, key: s.key + 1 }));
    }, 0);
  }

  render() {
    return (
      <div ref={this.ref}>
        {this.state.hasError ? null : (
          <div key={this.state.key}>{this.props.children}</div>
        )}
      </div>
    );
  }
}
