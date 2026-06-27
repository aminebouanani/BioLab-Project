import { useEffect, useState } from "react";
import { askReportQuestion, getChatHistory } from "../api/reportsApi.js";
import ErrorState from "./ErrorState.jsx";

export default function ChatPanel({ report }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const locked = !report?.latest_version || report.status === "OUTDATED";

  async function loadHistory() {
    if (!report?.report_id) return;
    try {
      setError("");
      setMessages(await getChatHistory(report.report_id));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadHistory();
  }, [report?.report_id]);

  async function sendQuestion(event) {
    event.preventDefault();
    if (!question.trim()) return;
    try {
      setLoading(true);
      setError("");
      await askReportQuestion(report.report_id, question.trim());
      setQuestion("");
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Report chatbot</h2>
      {locked && (
        <p className="lock-message">
          Chat is locked until an AI report exists and is not OUTDATED.
        </p>
      )}
      {error && <ErrorState message={error} onRetry={loadHistory} />}
      <div className="chat-history">
        {messages.length === 0 && <p className="small-text">No chat messages yet.</p>}
        {messages.map((message, index) => (
          <div key={`${message.created_at}-${index}`} className={`chat-message ${message.role}`}>
            <strong>{message.role === "assistant" ? "Assistant" : "Biologist"}</strong>
            <p>{message.message}</p>
          </div>
        ))}
      </div>
      <form onSubmit={sendQuestion} className="chat-form">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={locked || loading}
          placeholder="Ask about the generated report..."
        />
        <button disabled={locked || loading || !question.trim()}>
          {loading ? "Sending..." : "Send question"}
        </button>
      </form>
    </section>
  );
}
