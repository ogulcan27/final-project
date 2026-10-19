import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FlashPrice } from "./FlashPrice";

describe("FlashPrice", () => {
  it("does not flash on first render", () => {
    render(<FlashPrice price={100} testId="p" />);
    const el = screen.getByTestId("p");
    expect(el).toHaveTextContent("100.00");
    expect(el.className).not.toMatch(/flash-/);
  });

  it("flashes up on an uptick and down on a downtick", () => {
    const { rerender } = render(<FlashPrice price={100} testId="p" />);
    rerender(<FlashPrice price={101} testId="p" />);
    expect(screen.getByTestId("p")).toHaveClass("flash-up");
    rerender(<FlashPrice price={99.5} testId="p" />);
    expect(screen.getByTestId("p")).toHaveClass("flash-down");
  });

  it("shows a placeholder before the first price", () => {
    render(<FlashPrice price={null} testId="p" />);
    expect(screen.getByTestId("p")).toHaveTextContent("--");
  });
});
