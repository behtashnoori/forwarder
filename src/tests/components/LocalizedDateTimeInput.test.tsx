import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";

function Field(){const [value,setValue]=useState("2026-10-01T09:30");return <><LocalizedDateTimeInput aria-label="زمان" value={value} onChange={event=>setValue(event.target.value)}/><output>{localDateTimeInputToUtc(value)}</output></>;}
describe("shared localized date and time picker",()=>{
  it("switches calendar presentation without changing the logical instant",()=>{
    render(<Field/>);
    const input=screen.getByLabelText("زمان");
    const before=screen.getByText(/معادل میلادی/).textContent;
    fireEvent.click(screen.getByRole("button",{name:/شمسی/}));
    fireEvent.click(screen.getByRole("button",{name:"میلادی"}));
    expect(input).toHaveValue("2026-10-01T09:30");
    expect(screen.getByText(/معادل شمسی/).textContent).not.toBe(before);
    expect(screen.getByRole("status")).toHaveTextContent(new Date("2026-10-01T09:30").toISOString());
  });
  it("selects minute precision and preserves the existing local-to-UTC conversion",()=>{
    render(<Field/>);
    fireEvent.click(screen.getByRole("button",{name:/شمسی/}));
    fireEvent.change(screen.getByLabelText("زمان دقیقه"),{target:{value:"47"}});
    expect(screen.getByLabelText("زمان")).toHaveValue("2026-10-01T09:47");
    expect(screen.getByRole("status")).toHaveTextContent(new Date("2026-10-01T09:47").toISOString());
  });
});
