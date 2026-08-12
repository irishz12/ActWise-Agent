import { useState } from "react";
import ReactMarkdown from "react-markdown";

const API_URL = "http://127.0.0.1:8000";


function App() {
  const [message, setMessage] = useState("");
  const [clarification, setClarification] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function sendRequest(url, body) {
    const response = await fetch(`${API_URL}${url}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
  }

  async function runAgent() {
    if (!message.trim() || loading) {
      return;
    }

    setLoading(true);
    setResult(null);
    setClarification("");

    try {
      const data = await sendRequest("/agent/run", {
        message: message.trim(),
      });

      setResult(data);
    } catch (error) {
      setResult({
        error: error.message,
      });
    } finally {
      setLoading(false);
    }
  }

  async function resumeAgent() {
    if (
      !clarification.trim() ||
      !result?.thread_id ||
      loading
    ) {
      return;
    }

    setLoading(true);

    try {
      const data = await sendRequest("/agent/resume", {
        thread_id: result.thread_id,
        clarification: clarification.trim(),
      });

      setResult(data);
      setClarification("");
    } catch (error) {
      setResult({
        ...result,
        error: error.message,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">ACTWISE AGENT</p>
        <h1>Know when to act, ask, finish, or abstain.</h1>
        <p className="intro">
          A tool-using AI agent with explicit decision control.
        </p>
      </header>

      <section className="task-box">
        <textarea
          rows={4}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask ActWise to analyze the workspace..."
        />

        <button onClick={runAgent} disabled={loading}>
          {loading ? "Running..." : "Run task"}
        </button>
      </section>

      {result?.error && (
        <section className="error">
          {result.error}
        </section>
      )}

      {result && !result.error && (
        <section className="results">
          <div className="status-row">
            <div>
              <span className="label">Current decision</span>
              <h2>{result.decision}</h2>
            </div>

            <span className="thread">
              {result.thread_id?.slice(0, 8)}
            </span>
          </div>

          {result.paused && (
            <section className="clarify-card">
              <span className="label">
                ActWise needs clarification
              </span>

              <h3>
                {result.interrupt?.question ||
                  result.answer ||
                  "Please provide the missing information."}
              </h3>

              <div className="clarify-input">
                <input
                  value={clarification}
                  onChange={(event) =>
                    setClarification(event.target.value)
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      resumeAgent();
                    }
                  }}
                  placeholder="Enter clarification..."
                />

                <button
                  onClick={resumeAgent}
                  disabled={loading}
                >
                  {loading ? "Continuing..." : "Continue"}
                </button>
              </div>
            </section>
          )}

          {!result.paused && (
            <section className="card">
              <span className="label">Answer</span>
              <div className="markdown-answer">
                <ReactMarkdown>
                  {result.answer || ""}
                </ReactMarkdown>
              </div>
            </section>
          )}

          <div className="grid">
            <section className="card">
              <h3>Executed tools</h3>

              {result.tool_history?.length ? (
                result.tool_history.map((step, index) => (
                  <div
                    className="trace"
                    key={`${step.tool}-${index}`}
                  >
                    <strong>{step.tool}</strong>
                    <code>
                      {JSON.stringify(step.arguments)}
                    </code>
                  </div>
                ))
              ) : (
                <p className="muted">
                  No tools executed.
                </p>
              )}
            </section>

            <section className="card">
              <h3>Skipped tools</h3>

              {result.skipped_calls?.length ? (
                result.skipped_calls.map((step, index) => (
                  <div
                    className="trace"
                    key={`${step.tool}-${index}`}
                  >
                    <strong>{step.tool}</strong>
                    <p>{step.reason}</p>
                  </div>
                ))
              ) : (
                <p className="muted">
                  No tools skipped.
                </p>
              )}
            </section>
          </div>

          <section className="card">
            <h3>Decision history</h3>

            {result.decision_history?.map((step, index) => (
              <div className="decision" key={index}>
                <strong>{step.decision}</strong>
                <p>{step.reason}</p>
              </div>
            ))}
          </section>
        </section>
      )}
    </main>
  );
}


export default App;
