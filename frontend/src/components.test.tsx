import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModePill, Toggle, TransactionRow } from "./components";
import { demoTransactions } from "./demo";

describe("shared UI", () => {
  it("announces Roast state and toggles it", async () => {
    const onChange = vi.fn();
    render(<><ModePill enabled /><Toggle checked={false} label="Roast 모드" onChange={onChange} /></>);
    expect(screen.getByLabelText("Roast 켜짐")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "Roast 모드" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("shows real transaction amount and merchant", () => {
    render(<TransactionRow transaction={demoTransactions[0]} />);
    expect(screen.getByText("카페 온도")).toBeInTheDocument();
    expect(screen.getByText("12,000원")).toBeInTheDocument();
  });
});
