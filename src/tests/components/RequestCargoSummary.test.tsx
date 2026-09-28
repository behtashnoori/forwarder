import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import RequestCargoSummary from "@/components/RequestCargoSummary";
import { I18nProvider } from "@/i18n";
import type { RequestCargoItem } from "@/lib/api";
import { meaningfulCargoDescription } from "@/lib/cargoPresentation";

const cargoType = {
  public_id: "cargo-type-1",
  code: "GENERAL",
  fa_name: "کالای عمومی",
  en_name: "General cargo",
};
const uom = {
  public_id: "uom-1",
  code: "KG",
  fa_name: "کیلوگرم",
  en_name: "Kilogram",
  symbol: "kg",
  measurement_dimension: "WEIGHT" as const,
};
const pieceUom = {
  ...uom,
  public_id: "uom-2",
  code: "PIECE",
  fa_name: "عدد",
  en_name: "Piece",
  symbol: "pcs",
  measurement_dimension: "COUNT" as const,
};

describe("RequestCargoSummary human presentation", () => {
  beforeEach(() => window.localStorage.setItem("forwarder.language", "fa"));

  it.each([null, "", "   ", "ندارد", "ندارد.", "—"])("treats %s as an absent description", (value) => {
    expect(meaningfulCargoDescription(value)).toBeNull();
  });

  it("uses cargo type as the primary label, localized UOM, grouped quantity, and no placeholder", () => {
    const item: RequestCargoItem = {
      public_id: "cargo-item-1",
      position: 1,
      description: "ندارد.",
      cargo_type: cargoType,
      quantity: "1234.500000",
      uom,
    };
    render(<I18nProvider><RequestCargoSummary items={[item]} /></I18nProvider>);
    expect(screen.getByText(/کالای عمومی/)).toBeInTheDocument();
    expect(screen.getByText(/۱٬۲۳۴٫۵/)).toBeInTheDocument();
    expect(screen.getByText(/کیلوگرم/)).toBeInTheDocument();
    expect(screen.queryByText(/ندارد/)).not.toBeInTheDocument();
    expect(screen.queryByText(/kg/)).not.toBeInTheDocument();
  });

  it("honors the full title fallback order and preserves meaningful precision", () => {
    const items: RequestCargoItem[] = [
      {
        public_id: "cargo-item-explicit",
        position: 1,
        description: "قطعات خودرویی و مکانیکی",
        cargo_type: cargoType,
        quantity: "100.000000",
        uom: pieceUom,
      },
      {
        public_id: "cargo-item-type",
        position: 2,
        description: null,
        cargo_type: cargoType,
        quantity: "12.500000",
        uom,
      },
      {
        public_id: "cargo-item-neutral",
        position: 3,
        description: null,
        cargo_type: null,
        quantity: "12.500001",
        uom,
      },
    ];
    render(<I18nProvider><RequestCargoSummary items={items} /></I18nProvider>);
    expect(screen.getByText(/قطعات خودرویی و مکانیکی/)).toBeInTheDocument();
    expect(screen.getByText((_content, node) => node?.tagName === "SPAN" && node.textContent === "۱۰۰ عدد")).toBeInTheDocument();
    expect(screen.getByText(/۲\. کالای عمومی/)).toBeInTheDocument();
    expect(screen.getByText((_content, node) => node?.tagName === "SPAN" && node.textContent === "۱۲٫۵ کیلوگرم")).toBeInTheDocument();
    expect(screen.getByText(/قلم کالا ۳/)).toBeInTheDocument();
    expect(screen.getByText((_content, node) => node?.tagName === "SPAN" && node.textContent === "۱۲٫۵۰۰۰۰۱ کیلوگرم")).toBeInTheDocument();
  });
});
