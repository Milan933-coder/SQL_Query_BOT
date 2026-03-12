import { useState, useRef, useEffect } from "react";
import Plotly from "plotly.js-dist-min";

const SCHEMA = {
  ecommerce: {
    color: "#FF6B35",
    icon: "🛒",
    desc: "Customers, Products & Orders",
    questions: [
      "Show all customers from USA",
      "What is the total revenue from all orders?",
      "List top products by price",
      "Show all delivered orders",
    ],
  },
  hr: {
    color: "#4ECDC4",
    icon: "👥",
    desc: "Employees, Departments & Reviews",
    questions: [
      "List all active employees",
      "Which department has the highest budget?",
      "Show employees with salary above 100000",
      "Who got the highest performance score?",
    ],
  },
  inventory: {
    color: "#A78BFA",
    icon: "📦",
    desc: "Warehouses, Items & Shipments",
    questions: [
      "What items are stocked in Dallas?",
      "Show all inbound shipments",
      "Which item has highest quantity?",
      "List all warehouses with their cities",
    ],
  },
  crm: {
    color: "#F59E0B",
    icon: "🧭",
    desc: "Accounts, Managers & Interactions",
    questions: [
      "List account managers in EMEA",
      "Show active customer accounts by tier",
      "Which customers had escalated interactions?",
      "Find the account manager for customer 42",
    ],
  },
  finance: {
    color: "#22C55E",
    icon: "💳",
    desc: "Invoices, Payments & Refunds",
    questions: [
      "Show overdue invoices",
      "Total payments by method",
      "List refunds by reason",
      "Top customers by total invoice amount",
    ],
  },
};

const API = "http://localhost:8000";

function TypingDots() {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "8px 0" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#A78BFA",
            animation: "bounce 1.2s infinite",
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

function DBBadge({ name }) {
  if (!name) return null;
  const s = SCHEMA[name];
  return (
    <span style={{
      background: s?.color + "22", color: s?.color,
      border: `1px solid ${s?.color}55`,
      borderRadius: 20, padding: "2px 10px",
      fontSize: 11, fontWeight: 700, letterSpacing: 1,
      textTransform: "uppercase",
    }}>
      {s?.icon} {name}
    </span>
  );
}

function ResultTable({ columns, rows }) {
  if (!columns?.length) return <p style={{ color: "#888", fontStyle: "italic" }}>No results.</p>;
  return (
    <div style={{ overflowX: "auto", marginTop: 12 }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} style={{
                padding: "7px 12px", textAlign: "left",
                background: "#1a1a2e", color: "#A78BFA",
                borderBottom: "2px solid #A78BFA44",
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 600, fontSize: 11, letterSpacing: 0.8,
                textTransform: "uppercase", whiteSpace: "nowrap",
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? "#0f0f1a" : "#13131f" }}>
              {columns.map((c) => (
                <td key={c} style={{
                  padding: "7px 12px", color: "#d4d4f7",
                  borderBottom: "1px solid #ffffff0a",
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
                }}>
                  {String(row[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlotlyChart({ figure }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!figure || !chartRef.current) return;
    const data = figure.data || [];
    const layout = { margin: { t: 30, l: 40, r: 20, b: 40 }, paper_bgcolor: "#0a0a14", plot_bgcolor: "#0a0a14", font: { color: "#d4d4f7" }, ...figure.layout };
    const config = { responsive: true, displayModeBar: false, ...figure.config };
    Plotly.react(chartRef.current, data, layout, config);
    return () => Plotly.purge(chartRef.current);
  }, [figure]);

  return (
    <div style={{ marginTop: 12, border: "1px solid #ffffff12", borderRadius: 12, overflow: "hidden" }}>
      <div ref={chartRef} style={{ width: "100%", height: 320 }} />
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  const showSteps = Array.isArray(msg.steps) && msg.steps.length > 1;
  return (
    <div style={{
      display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 20, animation: "fadeSlide 0.3s ease",
    }}>
      {!isUser && (
        <div style={{
          width: 36, height: 36, borderRadius: "50%", flexShrink: 0,
          background: "linear-gradient(135deg, #A78BFA, #6D28D9)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, marginRight: 10, marginTop: 2,
          boxShadow: "0 0 12px #A78BFA55",
        }}>⚡</div>
      )}
      <div style={{ maxWidth: "75%", minWidth: 60 }}>
        {isUser ? (
          <div style={{
            background: "linear-gradient(135deg, #6D28D9, #4C1D95)",
            color: "#fff", padding: "10px 16px",
            borderRadius: "18px 18px 4px 18px",
            fontSize: 14, lineHeight: 1.6,
            boxShadow: "0 4px 15px #6D28D944",
          }}>{msg.content}</div>
        ) : (
          <div style={{
            background: "#13131f",
            border: "1px solid #ffffff12",
            color: "#d4d4f7", padding: "14px 16px",
            borderRadius: "4px 18px 18px 18px",
            fontSize: 14, lineHeight: 1.7,
            boxShadow: "0 4px 20px #00000044",
          }}>
            {msg.loading ? <TypingDots /> : (
              <>
                <div style={{ marginBottom: msg.data ? 10 : 0, color: "#e2e2f5" }}>
                  {msg.content}
                </div>
                {msg.database && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <DBBadge name={msg.database} />
                    {msg.attempts > 1 && (
                      <span style={{ fontSize: 11, color: "#F59E0B", background: "#F59E0B22",
                        border: "1px solid #F59E0B44", borderRadius: 20, padding: "2px 8px" }}>
                        ⚠️ Revalidated
                      </span>
                    )}
                  </div>
                )}
                {msg.sql && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{
                      cursor: "pointer", color: "#A78BFA", fontSize: 12,
                      fontFamily: "'JetBrains Mono', monospace", userSelect: "none",
                    }}>
                      ▸ View SQL Query
                    </summary>
                    <div style={{
                      background: "#0a0a14", border: "1px solid #A78BFA33",
                      borderRadius: 8, padding: "10px 14px", marginTop: 6,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12, color: "#c4b5fd", lineHeight: 1.8,
                      whiteSpace: "pre-wrap", wordBreak: "break-word",
                    }}>
                      {msg.sql}
                    </div>
                  </details>
                )}
                {msg.data && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>
                      {msg.data.count} row{msg.data.count !== 1 ? "s" : ""} returned
                    </div>
                    <ResultTable columns={msg.data.columns} rows={msg.data.rows} />
                  </div>
                )}
                {showSteps && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.8 }}>
                      Plan & Execution
                    </div>
                    {msg.steps.map((step, idx) => (
                      <div key={step.id || idx} style={{
                        border: "1px solid #ffffff12",
                        borderRadius: 12,
                        padding: "10px 12px",
                        marginBottom: 8,
                        background: "#0f0f1a"
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                          <div style={{ fontSize: 11, color: "#A78BFA", fontWeight: 700 }}>
                            Step {idx + 1} · {step.action}
                          </div>
                          {step.database && <DBBadge name={step.database} />}
                          {step.attempts > 1 && (
                            <span style={{ fontSize: 11, color: "#F59E0B", background: "#F59E0B22",
                              border: "1px solid #F59E0B44", borderRadius: 20, padding: "2px 8px" }}>
                              ⚠️ Revalidated
                            </span>
                          )}
                        </div>
                        {step.instruction && (
                          <div style={{ fontSize: 12, color: "#c5c5e6", marginBottom: 6 }}>
                            {step.instruction}
                          </div>
                        )}
                        {step.sql && (
                          <details style={{ marginTop: 6 }}>
                            <summary style={{
                              cursor: "pointer", color: "#A78BFA", fontSize: 12,
                              fontFamily: "'JetBrains Mono', monospace", userSelect: "none",
                            }}>
                              ▸ View SQL Query
                            </summary>
                            <div style={{
                              background: "#0a0a14", border: "1px solid #A78BFA33",
                              borderRadius: 8, padding: "10px 14px", marginTop: 6,
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 12, color: "#c4b5fd", lineHeight: 1.8,
                              whiteSpace: "pre-wrap", wordBreak: "break-word",
                            }}>
                              {step.sql}
                            </div>
                          </details>
                        )}
                        {step.columns && step.rows && (
                          <div style={{ marginTop: 8 }}>
                            <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>
                              {step.row_count} row{step.row_count !== 1 ? "s" : ""} returned
                            </div>
                            <ResultTable columns={step.columns} rows={step.rows} />
                          </div>
                        )}
                        {step.error && (
                          <div style={{ marginTop: 6, color: "#F87171", fontSize: 12 }}>
                            Error: {step.error}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {msg.plotly_message && (
                  <div style={{ marginTop: 10, fontSize: 12, color: "#F59E0B" }}>
                    {msg.plotly_message}
                  </div>
                )}
                {msg.plotly && <PlotlyChart figure={msg.plotly} />}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm your AI SQL Assistant. I can query 5 databases for you — ecommerce, HR, inventory, CRM, and finance.",
      id: 0,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [schema, setSchema] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const recorderRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetch(`${API}/schema`)
      .then((r) => r.json())
      .then(setSchema)
      .catch(() => {});
  }, []);

  const startRecording = async () => {
    if (isRecording || loading) return;
    setVoiceError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        try {
          const res = await fetch(`${API}/transcribe`, { method: "POST", body: form });
          const data = await res.json();
          if (data.text) {
            setInput((prev) => (prev ? `${prev} ${data.text}` : data.text));
            inputRef.current?.focus();
          } else if (data.detail) {
            setVoiceError(data.detail);
          } else {
            setVoiceError("Voice transcription failed.");
          }
        } catch (err) {
          setVoiceError("Could not reach transcription service.");
        }
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      setVoiceError("Microphone access denied or unavailable.");
    }
  };

  const stopRecording = () => {
    if (!recorderRef.current) return;
    recorderRef.current.stop();
    setIsRecording(false);
  };

  const sendMessage = async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");
    setLoading(true);

    const userMsg = { role: "user", content: q, id: Date.now() };
    const loadingMsg = { role: "assistant", content: "", loading: true, id: Date.now() + 1 };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      const res = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();

      const hasSteps = Array.isArray(data.steps) && data.steps.length > 1;
      const botMsg = {
        role: "assistant",
        id: Date.now() + 2,
        content: data.message,
        database: data.database,
        sql: data.sql,
        attempts: data.attempts,
        data: !hasSteps && data.success ? { columns: data.columns, rows: data.rows, count: data.row_count } : null,
        error: data.error,
        steps: data.steps || null,
        plotly: data.plotly || null,
        plotly_message: data.plotly_message || null,
      };

      setMessages((prev) => [...prev.slice(0, -1), botMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant", id: Date.now() + 2,
          content: "⚠️ Could not connect to backend. Make sure the server is running on port 8000.",
        },
      ]);
    }
    setLoading(false);
    inputRef.current?.focus();
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080810; font-family: 'Space Grotesk', sans-serif; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #0f0f1a; }
        ::-webkit-scrollbar-thumb { background: #3b3b6b; border-radius: 10px; }
        @keyframes bounce {
          0%, 100% { transform: translateY(0); opacity: 0.4; }
          50% { transform: translateY(-5px); opacity: 1; }
        }
        @keyframes fadeSlide {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 20px #A78BFA44; }
          50% { box-shadow: 0 0 35px #A78BFA88; }
        }
        @keyframes voice {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        .send-btn:hover { background: linear-gradient(135deg, #7C3AED, #5B21B6) !important; transform: scale(1.05); }
        .send-btn:active { transform: scale(0.97); }
        .voice-btn:hover { filter: brightness(1.05); transform: translateY(-1px); }
        .tab-btn:hover { background: #ffffff0a !important; }
        .quick-btn:hover { background: #ffffff08 !important; transform: translateY(-1px); }
      `}</style>

      <div style={{
        display: "flex", flexDirection: "column", height: "100vh",
        background: "#080810", color: "#d4d4f7",
      }}>
        {/* Header */}
        <div style={{
          padding: "16px 24px", background: "#0d0d1a",
          borderBottom: "1px solid #ffffff0f",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          animation: "glow 4s infinite",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: "linear-gradient(135deg, #A78BFA, #6D28D9)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, boxShadow: "0 0 20px #A78BFA55",
            }}>⚡</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 17, color: "#fff", letterSpacing: 0.5 }}>
                SQL Mind
              </div>
              <div style={{ fontSize: 11, color: "#A78BFA", letterSpacing: 1, textTransform: "uppercase" }}>
                Natural Language → SQL
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {Object.keys(SCHEMA).map((db) => (
              <div key={db} style={{
                background: SCHEMA[db].color + "15",
                border: `1px solid ${SCHEMA[db].color}33`,
                borderRadius: 20, padding: "3px 10px",
                fontSize: 11, color: SCHEMA[db].color, fontWeight: 600,
              }}>
                {SCHEMA[db].icon}
              </div>
            ))}
          </div>
        </div>

        {/* Tabs */}
        <div style={{
          display: "flex", background: "#0d0d1a",
          borderBottom: "1px solid #ffffff0a", padding: "0 24px",
        }}>
          {["chat", "databases"].map((tab) => (
            <button
              key={tab}
              className="tab-btn"
              onClick={() => setActiveTab(tab)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                padding: "10px 16px", fontSize: 13, fontWeight: 600,
                color: activeTab === tab ? "#A78BFA" : "#666",
                borderBottom: activeTab === tab ? "2px solid #A78BFA" : "2px solid transparent",
                transition: "all 0.2s", marginBottom: -1, letterSpacing: 0.5,
                borderRadius: 0,
              }}
            >
              {tab === "chat" ? "💬 Chat" : "🗄️ Databases"}
            </button>
          ))}
        </div>

        {/* Main Area */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {activeTab === "chat" ? (
            <>
              {/* Messages */}
              <div style={{ flex: 1, overflowY: "auto", padding: "24px 24px 8px" }}>
                {messages.map((msg) => <Message key={msg.id} msg={msg} />)}
                <div ref={bottomRef} />
              </div>

              {/* Quick suggestions */}
              <div style={{
                padding: "8px 24px 0", display: "flex", gap: 8, flexWrap: "wrap",
              }}>
                {["Show all customers from USA", "Which dept has highest budget?", "What items are in Dallas?", "Show overdue invoices"].map((q) => (
                  <button
                    key={q}
                    className="quick-btn"
                    onClick={() => sendMessage(q)}
                    disabled={loading}
                    style={{
                      background: "#ffffff05", border: "1px solid #ffffff15",
                      borderRadius: 20, padding: "5px 12px",
                      fontSize: 12, color: "#8888aa", cursor: "pointer",
                      transition: "all 0.2s", fontFamily: "inherit",
                    }}
                  >{q}</button>
                ))}
              </div>

              {/* Input */}
              <div style={{ padding: "12px 24px 20px" }}>
                <div style={{
                  display: "flex", gap: 10, background: "#13131f",
                  border: "1px solid #ffffff15", borderRadius: 16,
                  padding: "8px 8px 8px 16px",
                  boxShadow: "0 0 30px #00000055",
                  transition: "border-color 0.2s",
                }}>
                  <button
                    className="voice-btn"
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={loading}
                    style={{
                      background: isRecording ? "linear-gradient(135deg, #EF4444, #B91C1C)" : "linear-gradient(135deg, #0EA5E9, #2563EB)",
                      border: "none", borderRadius: 10, padding: "8px 12px",
                      cursor: loading ? "not-allowed" : "pointer",
                      color: "#fff", fontWeight: 700, fontSize: 12,
                      opacity: loading ? 0.4 : 1,
                      transition: "all 0.2s", fontFamily: "inherit",
                      minWidth: 72,
                    }}
                  >
                    {isRecording ? "Stop" : "Voice"}
                  </button>
                  <input
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    disabled={loading}
                    placeholder="Ask anything about your data... (e.g. 'Show top 5 employees by salary')"
                    style={{
                      flex: 1, background: "none", border: "none", outline: "none",
                      color: "#e2e2f5", fontSize: 14, fontFamily: "inherit",
                      caretColor: "#A78BFA",
                    }}
                  />
                  <button
                    className="send-btn"
                    onClick={() => sendMessage()}
                    disabled={loading || !input.trim()}
                    style={{
                      background: "linear-gradient(135deg, #8B5CF6, #6D28D9)",
                      border: "none", borderRadius: 10, padding: "8px 18px",
                      cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                      color: "#fff", fontWeight: 700, fontSize: 14,
                      opacity: loading || !input.trim() ? 0.4 : 1,
                      transition: "all 0.2s", fontFamily: "inherit",
                    }}
                  >
                    {loading ? "..." : "→"}
                  </button>
                </div>
                {isRecording && (
                  <div style={{
                    height: 6, borderRadius: 999, marginTop: 8,
                    background: "linear-gradient(90deg, #0EA5E9, #8B5CF6, #F59E0B)",
                    backgroundSize: "200% 100%",
                    animation: "voice 1.2s linear infinite",
                    boxShadow: "0 0 12px #0EA5E955",
                  }} />
                )}
                {voiceError && (
                  <div style={{ marginTop: 8, fontSize: 11, color: "#F87171", textAlign: "center" }}>
                    {voiceError}
                  </div>
                )}
                <div style={{ fontSize: 11, color: "#444", marginTop: 8, textAlign: "center" }}>
                  Powered by Gemini (Orchestrator) + GPT-4o-mini (Coder) · Plan & Execute · 1-retry revalidation loop
                </div>
              </div>
            </>
          ) : (
            /* Database Explorer */
            <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
              <div style={{ marginBottom: 20 }}>
                <h2 style={{ color: "#fff", fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
                  Database Explorer
                </h2>
                <p style={{ color: "#666", fontSize: 13 }}>
                  All 5 SQLite databases with their tables and columns
                </p>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
                {Object.entries(SCHEMA).map(([dbName, info]) => (
                  <div key={dbName} style={{
                    background: "#0d0d1a", border: `1px solid ${info.color}33`,
                    borderRadius: 16, overflow: "hidden",
                    boxShadow: `0 4px 20px ${info.color}11`,
                  }}>
                    <div style={{
                      padding: "14px 18px", background: info.color + "18",
                      borderBottom: `1px solid ${info.color}22`,
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 22 }}>{info.icon}</span>
                        <div>
                          <div style={{ fontWeight: 700, color: info.color, textTransform: "capitalize" }}>
                            {dbName}
                          </div>
                          <div style={{ fontSize: 11, color: "#777", marginTop: 1 }}>{info.desc}</div>
                        </div>
                      </div>
                    </div>
                    <div style={{ padding: 16 }}>
                      {schema?.[dbName] && Object.entries(schema[dbName].tables).map(([table, cols]) => (
                        <div key={table} style={{ marginBottom: 12 }}>
                          <div style={{
                            fontSize: 12, fontWeight: 700, color: "#fff",
                            fontFamily: "'JetBrains Mono', monospace",
                            marginBottom: 4,
                          }}>
                            📋 {table}
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                            {cols.map((col) => (
                              <span key={col} style={{
                                background: info.color + "15",
                                color: info.color + "cc",
                                border: `1px solid ${info.color}22`,
                                borderRadius: 6, padding: "2px 8px",
                                fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                              }}>{col}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                      <div style={{ borderTop: "1px solid #ffffff0a", paddingTop: 12, marginTop: 4 }}>
                        <div style={{ fontSize: 11, color: "#555", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.8 }}>
                          Sample questions
                        </div>
                        {info.questions.map((q) => (
                          <button
                            key={q}
                            className="quick-btn"
                            onClick={() => { setActiveTab("chat"); setTimeout(() => sendMessage(q), 100); }}
                            style={{
                              display: "block", width: "100%", textAlign: "left",
                              background: "#ffffff04", border: "1px solid #ffffff0a",
                              borderRadius: 8, padding: "6px 10px", marginBottom: 5,
                              fontSize: 12, color: "#8888aa", cursor: "pointer",
                              transition: "all 0.15s", fontFamily: "inherit",
                            }}
                          >
                            ▸ {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
