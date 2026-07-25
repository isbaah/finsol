import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCollectionsChart } from "@/features/dashboards/api";

import { CollectionsChart } from "./collections-chart";

vi.mock("@/features/dashboards/api", () => ({
  getCollectionsChart: vi.fn(),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("CollectionsChart", () => {
  beforeEach(() => {
    vi.mocked(getCollectionsChart).mockReset();
  });

  it("shows a meaningful empty state when no months have activity", async () => {
    vi.mocked(getCollectionsChart).mockResolvedValue([
      { month: "2026-06-01", expected: "0.00", collected: "0.00" },
      { month: "2026-07-01", expected: "0.00", collected: "0.00" },
    ]);
    renderWithProviders(<CollectionsChart />);

    expect(
      await screen.findByText(/No repayments were expected or collected/),
    ).toBeInTheDocument();
  });

  it("defaults to six months and refetches when switched to twelve", async () => {
    vi.mocked(getCollectionsChart).mockResolvedValue([]);
    const user = userEvent.setup();
    renderWithProviders(<CollectionsChart />);

    await waitFor(() => expect(getCollectionsChart).toHaveBeenCalledWith(6));
    const twelveButton = screen.getByRole("button", { name: "12 months" });
    expect(twelveButton).toHaveAttribute("aria-pressed", "false");

    await user.click(twelveButton);

    await waitFor(() => expect(getCollectionsChart).toHaveBeenCalledWith(12));
    expect(screen.getByRole("button", { name: "12 months" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("shows an error message when the series cannot load", async () => {
    vi.mocked(getCollectionsChart).mockRejectedValue(new Error("boom"));
    renderWithProviders(<CollectionsChart />);

    expect(await screen.findByText(/Couldn't load the chart/)).toBeInTheDocument();
  });
});
