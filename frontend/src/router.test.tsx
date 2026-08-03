import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { BrowserRouter, Link, NavLink, Route, Routes, useParams } from "./router";

function ParamPage() {
  const { transactionId } = useParams<{ transactionId: string }>();
  return <h1>거래 {transactionId}</h1>;
}

describe("internal browser router", () => {
  beforeEach(() => window.history.replaceState({}, "", "/"));

  it("navigates without reloading and resolves path params", () => {
    render(
      <BrowserRouter>
        <Link to="/transactions/tx-123?demo=1">거래 열기</Link>
        <Routes>
          <Route path="/" element={<p>홈</p>} />
          <Route path="/transactions/:transactionId" element={<ParamPage />} />
        </Routes>
      </BrowserRouter>,
    );

    fireEvent.click(screen.getByRole("link", { name: "거래 열기" }));

    expect(screen.getByRole("heading", { name: "거래 tx-123" })).toBeInTheDocument();
    expect(window.location.search).toBe("?demo=1");
  });

  it("marks only the matching navigation link as current", () => {
    window.history.replaceState({}, "", "/agent");
    render(
      <BrowserRouter>
        <NavLink to="/">홈</NavLink>
        <NavLink to="/agent">에이전트</NavLink>
      </BrowserRouter>,
    );

    expect(screen.getByRole("link", { name: "에이전트" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "홈" })).not.toHaveAttribute("aria-current");
  });
});
