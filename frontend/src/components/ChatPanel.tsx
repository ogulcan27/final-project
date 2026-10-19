"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { getChatHistory, sendChat } from "@/lib/api";
import { formatPrice, formatQty } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

interface Props {
  onActions: () => void;
  onCollapse: () => void;
}

/** AI assistant sidebar: history, input, loading indicator, inline trade / watchlist confirmations. */
export function ChatPanel({ onActions, onCollapse }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    getChatHistory()
      .then((rows) => active && setMessages((m) => [...rows, ...m]))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages, loading]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await sendChat(text);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.message, trades: res.trades, watchlist_changes: res.watchlist_changes },
      ]);
      if (res.trades.length || res.watchlist_changes.length) onActions();
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${(err as Error).message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="flex h-full w-full flex-col border border-line bg-panel">
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-line px-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-accent">FinAlly AI</h2>
        <button onClick={onCollapse} title="Collapse chat" className="text-xs text-muted hover:text-text">
          &raquo;
        </button>
      </header>
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && !loading && (
          <p className="text-xs text-muted">
            Ask about your portfolio, request analysis, or tell me to trade. Try: &quot;Buy 5 NVDA&quot;.
          </p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && (
          <div data-testid="chat-loading" className="flex items-center gap-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue [animation-delay:300ms]" />
            <span className="ml-1">Thinking</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex gap-1 border-t border-line p-2">
        <input
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly..."
          className="min-w-0 flex-1 border border-line bg-bg px-2 py-1.5 text-xs outline-none focus:border-blue"
        />
        <button
          data-testid="chat-send"
          type="submit"
          disabled={loading}
          className="bg-purple px-3 text-xs font-semibold text-text hover:brightness-125 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div data-testid="chat-message" data-role={message.role} className={isUser ? "pl-6" : "pr-6"}>
      <div className="mb-0.5 text-[10px] uppercase tracking-widest text-muted">{isUser ? "You" : "FinAlly"}</div>
      <div
        className={`whitespace-pre-wrap px-2 py-1.5 text-xs leading-relaxed ${
          isUser ? "bg-blue/15 text-text" : "border-l-2 border-accent bg-panel-2 text-text"
        }`}
      >
        {message.content}
      </div>
      {message.trades?.map((t, i) => (
        <ActionLine key={`t${i}`} failed={t.status === "failed"} error={t.error}>
          {t.side.toUpperCase()} {formatQty(t.quantity)} {t.ticker}
          {t.price != null && ` @ ${formatPrice(t.price)}`}
        </ActionLine>
      ))}
      {message.watchlist_changes?.map((w, i) => (
        <ActionLine key={`w${i}`} failed={w.status === "failed"} error={w.error}>
          WATCHLIST {w.action === "add" ? "+" : "-"} {w.ticker}
        </ActionLine>
      ))}
    </div>
  );
}

function ActionLine({ failed, error, children }: { failed: boolean; error?: string | null; children: React.ReactNode }) {
  return (
    <div
      data-testid="chat-action"
      className={`mt-1 border px-2 py-1 font-mono text-[11px] ${
        failed ? "border-down/50 text-down" : "border-up/50 text-up"
      }`}
    >
      {failed ? "FAILED " : "EXECUTED "}
      {children}
      {failed && error && <span className="text-muted"> - {error}</span>}
    </div>
  );
}
