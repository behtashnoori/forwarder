import { ReactNode, useEffect, useState } from "react";
import { getOperationalContext } from "@/lib/api";
export default function OperationalAnyPermission({permissions,children}:{permissions:string[];children:ReactNode}){
 const [allowed,setAllowed]=useState(false);
 const permissionKey=permissions.join("|");
 useEffect(()=>{const required=permissionKey.split("|");getOperationalContext().then(r=>setAllowed(required.some(p=>r.data.permissions.includes(p)))).catch(()=>setAllowed(false));},[permissionKey]);
 return allowed?<>{children}</>:null;
}
