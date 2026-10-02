import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import RequestedEndpointComparison from "@/components/RequestedEndpointComparison";
import type { OperationalLocationRef, RequestedEndpoints } from "@/lib/api";

const endpoint = {label:"شهر درخواستی",reference:{source_type:"city",source_id:2773,country_id:1},reusable:true,province_id:129,country_id:1} as RequestedEndpoints["origin"];
it.each([
  [{source_type:"city",source_id:4383}, "متفاوت است"],
  [{source_type:"province",source_id:129}, "نوع یا دقت مکانی متفاوت"],
  [{source_type:"logistics_point",source_id:"point-1"}, "نوع یا دقت مکانی متفاوت"],
] as const)("keeps explicit difference distinct from geographic precision (%j)", (reference,notice) => {
  render(<RequestedEndpointComparison requested={{origin:endpoint,destination:endpoint}} origin={{label:"محل عملیاتی",reference:reference as OperationalLocationRef}} destination={{label:endpoint.label,reference:endpoint.reference}}/>);
  expect(screen.getByText(new RegExp(notice))).toBeInTheDocument();
  expect(screen.getByText(/این نمایش، تأیید یا دلیل تاریخی تفاوت نیست/)).toBeInTheDocument();
});
