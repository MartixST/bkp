import Chatbot from "./Chatbot";
import "./styles/theme.css";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <div style={{ minHeight: "100vh" }}>
      <h1 style={{ padding: 16 }}>Home page</h1>
      <ErrorBoundary>
        <Chatbot />
      </ErrorBoundary>
    </div>
  );
}
