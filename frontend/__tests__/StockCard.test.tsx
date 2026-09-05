import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import StockCard from "@/components/StockCard";
import type { MarketQuote } from "@/types";

const baseQuote: MarketQuote = {
  symbol: "RELIANCE",
  company_name: "Reliance Industries",
  price: 2950.5,
  percent_change: 4.8,
  volume: 100000,
  chart_points: [2800, 2820, 2900, 2950.5],
  last_updated: new Date().toISOString(),
  is_stale: false,
};

describe("StockCard", () => {
  it("renders the symbol and price", () => {
    render(<StockCard quote={baseQuote} />);
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("₹2950.50")).toBeInTheDocument();
  });

  it("shows a friendly message when the quote failed to load", () => {
    render(<StockCard quote={{ ...baseQuote, price: null, error: "invalid_symbol_or_no_data" }} />);
    expect(screen.getByText(/isn't available right now/)).toBeInTheDocument();
  });
});
