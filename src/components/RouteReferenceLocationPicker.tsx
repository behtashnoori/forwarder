import CanonicalLocationPicker, {type CanonicalEndpointRef} from "@/components/CanonicalLocationPicker";

export type RouteReferenceEndpointRef = CanonicalEndpointRef;

export function RouteReferenceLocationPicker({label,value,onChange}:{
  id:string; label:string; value:RouteReferenceEndpointRef|null;
  onChange:(value:RouteReferenceEndpointRef|null)=>void;
}) {
  return <CanonicalLocationPicker label={label} value={value} onChange={onChange}/>;
}
