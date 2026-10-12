import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CurrencyInput, Dialog, ModePill, Toggle, TransactionRow } from "./components";
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

  it("contains keyboard focus, closes on Escape and restores the opener", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return <><button onClick={() => setOpen(true)}>수정 열기</button>{open &&
        <Dialog aria-label="수정" onClose={() => setOpen(false)}>
          <input aria-label="이름" /><button onClick={() => setOpen(false)}>취소</button>
        </Dialog>}</>;
    }
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "수정 열기" });
    await user.click(opener);
    expect(screen.getByRole("dialog", { name: "수정" })).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("이름")).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "취소" })).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("이름")).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("does not dismiss a dialog while a save is in progress", async () => {
    const onClose = vi.fn();
    render(<Dialog aria-label="저장" busy onClose={onClose}><button disabled>저장 중</button></Dialog>);
    await userEvent.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
  });

});
