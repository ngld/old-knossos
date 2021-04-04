import React from 'react';
import { Callout } from '@blueprintjs/core';

interface ErrorWrapperProps {}
interface ErrorWrapperState {
  error: Error | null;
  info: React.ErrorInfo | null;
}

export default class ErrorBoundary extends React.Component<ErrorWrapperProps, ErrorWrapperState> {
  constructor(props: ErrorWrapperProps) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ info: errorInfo });
  }

  render() {
    if (this.state.error) {
      return (
        <Callout intent="danger" title="Error">
          <div className="text-white overflow-auto">
            Encountered error during rendering:
            <br />
            <pre>{this.state.error.stack ?? this.state.error.toString()}</pre>
            {this.state.info !== null && (
              <div>
                Component stack:
                <br />
                <pre>{this.state.info.componentStack}</pre>
              </div>
            )}
          </div>
        </Callout>
      );
    } else {
      return this.props.children;
    }
  }
}
