"use client";

import { useState } from "react";
import { formatPrice } from "@/lib/format";

interface Props {
  price: number | null | undefined;
  testId?: string;
  className?: string;
}

/** Price text that briefly flashes green on an uptick and red on a downtick. */
export function FlashPrice({ price, testId, className = "" }: Props) {
  const [prev, setPrev] = useState(price);
  const [flash, setFlash] = useState("");

  if (price !== prev) {
    setPrev(price);
    if (price != null && prev != null) setFlash(price > prev ? "flash-up" : "flash-down");
  }

  return (
    <span
      key={price ?? "none"}
      data-testid={testId}
      className={`rounded px-1 tabular-nums ${flash} ${className}`}
      onAnimationEnd={() => setFlash("")}
    >
      {formatPrice(price)}
    </span>
  );
}
