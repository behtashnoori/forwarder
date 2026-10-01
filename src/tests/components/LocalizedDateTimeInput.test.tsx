import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";

function Field(){const [value,setValue]=useState("");return <><LocalizedDateTimeInput aria-label="زمان" value={value} onChange={event=>setValue(event.target.value)}/><output>{localDateTimeInputToUtc(value)}</output></>;}
describe("localized wall-clock entry",()=>{
  it("accepts Persian digits without changing the existing local timezone conversion",()=>{
    render(<Field/>);
    const input=screen.getByLabelText("زمان");
    fireEvent.change(input,{target:{value:"۲۰۲۶-۱۰-۰۱ ۰۹:۳۰"}});
    expect(input).toHaveValue("2026-10-01T09:30");
    expect(input).toBeValid();
    expect(screen.getByRole("status")).toHaveTextContent(new Date("2026-10-01T09:30").toISOString());
    expect(input).toHaveAttribute("dir","ltr");
  });
  it("rejects impossible dates instead of silently rolling to the next month",()=>{
    render(<Field/>);
    const input=screen.getByLabelText("زمان");
    fireEvent.change(input,{target:{value:"2026-02-30T09:30"}});
    expect(input).toBeInvalid();
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });
});
