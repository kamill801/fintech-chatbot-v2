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

function CurrencyFormHarness({ onSubmit }: { onSubmit(): void }) {
  const [value, setValue] = useState(12_800);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <CurrencyInput ariaLabel="지출 금액" value={value} onChange={setValue} />
      <button type="submit">기록하기</button>
    </form>
  );
}

describe("shared UI", () => {
  it("announces the Korean grandma mode state and toggles it", async () => {
    const onChange = vi.fn();
    render(<><ModePill enabled /><Toggle checked={false} label="욕쟁이 할머니 모드" onChange={onChange} /></>);
    expect(screen.getByLabelText("욕쟁이 할머니 모드 켜짐")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "욕쟁이 할머니 모드" }));
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

  it("submits a form after formatting the amount with commas", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyFormHarness onSubmit={onSubmit} />);
    const input = screen.getByLabelText("지출 금액");

    expect(input).toHaveValue("12,800");
    expect(input).toBeValid();
    await user.click(screen.getByRole("button", { name: "기록하기" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("renders one clear bookkeeper symbol without stacked icons", () => {
    render(<BookkeeperMark />);
    expect(screen.getByLabelText("장부지기").querySelectorAll("svg")).toHaveLength(1);
  });
});
