import { useState, useRef, useEffect } from "react";
import { queryReasoning } from "../api/client";

const MODES = [
  { key: "RECALL", desc: "Tra cứu nguyên văn từ memory. Không suy diễn." },
  { key: "SYNTHESIZE", desc: "Tổng hợp nhiều memory thành structured summary." },
  { key: "REFLECT", desc: "Phân tích evolution tư duy, nhận diện pattern." },
  { key: "CHALLENGE", desc: "Chỉ ra mâu thuẫn, logic yếu, gaps." },
  { key: "EXPAND", desc: "Mở rộng kiến thức với external knowledge." },
];

export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("RECALL");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: query, mode }]);
    setLoading(true);

    try {
      const res = await queryReasoning({ query, mode });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.response,
          mode: res.mode,
          memoryUsed: res.memory_used?.length || 0,
          tokens: res.token_usage?.total || 0,
          latency: res.latency_ms,
          external: res.external_knowledge_used,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message },
      ]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = (e) => {
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  };

  const activeMode = MODES.find((m) => m.key === mode);

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Reasoning Chat</h2>
        <div className="mode-selector">
          {MODES.map((m) => (
            <button
              key={m.key}
              className={`mode-btn ${mode === m.key ? "active" : ""}`}
              onClick={() => setMode(m.key)}
            >
              {m.key}
            </button>
          ))}
        </div>
        <div className="mode-desc">{activeMode?.desc}</div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-icon">🧠</div>
            <p>Chọn mode và bắt đầu trò chuyện với bộ nhớ của bạn</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-bubble">{msg.text}</div>
            {msg.role === "assistant" && (
              <div className="message-meta">
                <span className="message-mode">{msg.mode}</span>
                <span>🧠 {msg.memoryUsed} memories</span>
                <span>⚡ {msg.tokens} tokens</span>
                <span>⏱ {msg.latency}ms</span>
                {msg.external && <span className="badge info">External</span>}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-bubble">
              <div className="loading-dots">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoResize(e); }}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi về memory của bạn... (Enter để gửi, Shift+Enter xuống dòng)"
            rows={1}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            ▶
          </button>
        </div>
      </div>
    </div>
  );
}
