import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

const DefaultErrorFallback = ({
  error,
  errorInfo,
  onRetry,
}: {
  error?: Error;
  errorInfo?: ErrorInfo;
  onRetry: () => void;
}) => {
  const { direction, t } = useI18n();
  const iconSpacingClass = direction === "rtl" ? "ml-2" : "mr-2";

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <CardTitle className="text-xl text-gray-900">
            {t("errorBoundary.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-gray-600">
            {t("errorBoundary.description")}
          </p>

          {process.env.NODE_ENV === "development" && error && (
            <details className="text-left bg-gray-50 p-3 rounded-lg">
              <summary className="cursor-pointer font-medium text-sm text-gray-700">
                {t("errorBoundary.details")}
              </summary>
              <pre className="mt-2 text-xs text-red-600 overflow-auto">
                {error.toString()}
                {errorInfo?.componentStack}
              </pre>
            </details>
          )}

          <div className="flex gap-2 justify-center">
            <Button onClick={onRetry} variant="outline">
              <RefreshCw className={`w-4 h-4 ${iconSpacingClass}`} />
              {t("errorBoundary.retry")}
            </Button>
            <Button onClick={() => window.location.reload()}>
              {t("errorBoundary.reload")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <DefaultErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
