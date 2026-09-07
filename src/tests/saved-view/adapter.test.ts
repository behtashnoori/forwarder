import {describe,expect,it} from "vitest";
import {applySavedViewDefinition,toSavedViewDefinition,unsupportedSavedViewFilters} from "@/saved-view/operational-shipments-adapter";

const filters={status:"in_progress",customer:"",origin:"",destination:"",overdue:"",date_from:"2026-01-01",date_to:"2026-01-31"};
describe("operational shipment saved-view adapter",()=>{
 it("roundtrips the governed population contract",()=>{const definition=toSavedViewDefinition(filters);expect(applySavedViewDefinition(definition,{...filters,status:"",date_from:"",date_to:""})).toEqual(filters);expect(definition.query_definition.metric_keys).toEqual(["SHIPMENT_COUNT"]);});
 it("reports filters the semantic surface cannot safely persist",()=>expect(unsupportedSavedViewFilters({...filters,origin:"Tehran"})).toEqual(["origin"]));
});
