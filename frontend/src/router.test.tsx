import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter, Link, NavLink, Route, Routes, useNavigate, useParams } from "./router";

function ParamPage() {
  const { transactionId } = useParams<{ transactionId: string }>();
  return <h1>거래 {transactionId}</h1>;
}

function BackButton() {
  const navigate = useNavigate();
  return <button onClick={() => navigate(-1)}>뒤로</button>;
}

describe("internal browser router", () => {
  beforeEach(() => window.history.replaceState({}, "", "/"));
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

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

  it("keeps a direct-link back action inside the app and preserves demo mode", () => {
    window.history.replaceState({}, "", "/add?demo=1");
    const go = vi.spyOn(window.history, "go").mockImplementation(() => {});
    render(<BrowserRouter><BackButton /></BrowserRouter>);
    fireEvent.click(screen.getByRole("button", { name: "뒤로" }));
    expect(go).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/");
    expect(window.location.search).toBe("?demo=1");
    go.mockRestore();
  });

  it("uses the browser history when a prior in-app entry exists", () => {
    const go = vi.spyOn(window.history, "go").mockImplementation(() => {});
    render(<BrowserRouter><Link to="/add">기록</Link><BackButton /></BrowserRouter>);
    fireEvent.click(screen.getByRole("link", { name: "기록" }));
    fireEvent.click(screen.getByRole("button", { name: "뒤로" }));
    expect(go).toHaveBeenCalledWith(-1);
    go.mockRestore();
  });

  it("rejects malformed URL parameters without crashing the page", () => {
    window.history.replaceState({}, "", "/transactions/%E0%A4%A");
    render(<BrowserRouter><Routes>
      <Route path="/transactions/:transactionId" element={<ParamPage />} />
      <Route path="*" element={<p>페이지를 찾을 수 없어요</p>} />
    </Routes></BrowserRouter>);
    expect(screen.getByText("페이지를 찾을 수 없어요")).toBeInTheDocument();
  });
});
