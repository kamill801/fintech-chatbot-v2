import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BookkeeperMark, CurrencyInput, ModePill, Toggle, TransactionRow } from "./components";
import { demoTransactions } from "./demo";

function CurrencyHarness() {
  const [value, setValue] = useState(1);
  return <CurrencyInput ariaLabel="생활비 예산 금액" minimum={1} value={value} onChange={setValue} />;
}

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

  it("lets the user clear and replace a won amount without a sticky leading digit", async () => {
    const user = userEvent.setup();
    render(<CurrencyHarness />);
    const input = screen.getByLabelText("생활비 예산 금액");

    await user.click(input);
    await user.clear(input);
    expect(input).toHaveValue("");

    await user.type(input, "800000");
    await user.tab();
    expect(input).toHaveValue("800,000");
    expect(input).toHaveAttribute("inputmode", "numeric");
  });

  it("renders one clear bookkeeper symbol without stacked icons", () => {
    render(<BookkeeperMark />);
    expect(screen.getByLabelText("장부지기").querySelectorAll("svg")).toHaveLength(1);
  });
});
