import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoProfile } from "../demo";
import { BrowserRouter } from "../router";
import { ProfileSettingsPage } from "./ProfileSettings";

const mocks = vi.hoisted(() => ({ useLedger: vi.fn(), saveProfile: vi.fn() }));

vi.mock("../ledger-context", () => ({ useLedger: mocks.useLedger }));

describe("profile settings editing", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/settings/budget");
    mocks.saveProfile.mockReset().mockResolvedValue(demoProfile);
    mocks.useLedger.mockReturnValue({ demo: false, profile: demoProfile, saveProfile: mocks.saveProfile });
  });
  afterEach(cleanup);

  it("prefills the existing budget and saves a changed amount", async () => {
    const user = userEvent.setup();
    render(<BrowserRouter><ProfileSettingsPage section="budget" /></BrowserRouter>);

    expect(screen.getByRole("textbox", { name: "생활비 예산" })).toHaveValue("800,000");
    const budget = screen.getByRole("textbox", { name: "생활비 예산" });
    await user.clear(budget);
    await user.type(budget, "700000");
    await user.click(screen.getByRole("button", { name: "변경사항 저장" }));

    await waitFor(() => expect(mocks.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ discretionary_budget_krw: 700000 })));
    expect(window.location.pathname).toBe("/settings");
  });

  it("keeps the existing goal when editing the budget and shows a shortage", () => {
    mocks.useLedger.mockReturnValue({ demo: false, profile: { ...demoProfile, monthly_income_krw: 1 }, saveProfile: mocks.saveProfile });
    render(<BrowserRouter><ProfileSettingsPage section="budget" /></BrowserRouter>);

    expect(screen.getByText(/부족/)).toBeInTheDocument();
    expect(mocks.saveProfile).not.toHaveBeenCalled();
  });
});
