import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatPanel, MessageBubble } from "./ChatPanel";

function jsonResponse(body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

afterEach(() => vi.unstubAllGlobals());

describe("MessageBubble", () => {
  it("renders executed and failed actions inline", () => {
    render(
      <MessageBubble
        message={{
          role: "assistant",
          content: "Done.",
          trades: [
            { ticker: "AAPL", side: "buy", quantity: 1, price: 190.5, status: "executed" },
            { ticker: "TSLA", side: "sell", quantity: 5, status: "failed", error: "Insufficient shares" },
          ],
          watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed" }],
        }}
      />,
    );
    expect(screen.getByTestId("chat-message")).toHaveTextContent("Done.");
    const actions = screen.getAllByTestId("chat-action");
    expect(actions[0]).toHaveTextContent("EXECUTED BUY 1 AAPL @ 190.50");
    expect(actions[1]).toHaveTextContent("FAILED SELL 5 TSLA - Insufficient shares");
    expect(actions[2]).toHaveTextContent("WATCHLIST + PYPL");
  });
});

describe("ChatPanel", () => {
  it("shows a loading indicator until the reply arrives, then calls onActions", async () => {
    let resolveChat!: (r: Response) => void;
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/chat/history") return jsonResponse([]);
      return new Promise<Response>((r) => (resolveChat = r));
    });
    vi.stubGlobal("fetch", fetchMock);
    const onActions = vi.fn();
    render(<ChatPanel onActions={onActions} onCollapse={() => {}} />);

    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "buy AAPL" } });
    fireEvent.click(screen.getByTestId("chat-send"));

    expect(await screen.findByTestId("chat-loading")).toBeInTheDocument();
    expect(screen.getAllByTestId("chat-message")[0]).toHaveTextContent("buy AAPL");

    resolveChat(
      new Response(
        JSON.stringify({
          message: "Bought 1 AAPL",
          trades: [{ ticker: "AAPL", side: "buy", quantity: 1, price: 190, status: "executed", error: null }],
          watchlist_changes: [],
        }),
      ),
    );

    await waitFor(() => expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument());
    expect(screen.getAllByTestId("chat-message")).toHaveLength(2);
    expect(screen.getByTestId("chat-action")).toHaveTextContent("EXECUTED BUY 1 AAPL");
    expect(onActions).toHaveBeenCalledOnce();
  });

  it("loads stored history with actions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse([
          { role: "user", content: "hi", actions: null, created_at: "" },
          {
            role: "assistant",
            content: "added",
            actions: { trades: [], watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed" }] },
            created_at: "",
          },
        ]),
      ),
    );
    render(<ChatPanel onActions={() => {}} onCollapse={() => {}} />);
    expect(await screen.findByText("added")).toBeInTheDocument();
    expect(screen.getByTestId("chat-action")).toHaveTextContent("WATCHLIST + PYPL");
  });
});
