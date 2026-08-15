import {readFileSync} from "node:fs";
import {join} from "node:path";
import {describe,expect,it} from "vitest";

describe("Admin Panel document authority contract",()=>{
 const source=readFileSync(join(process.cwd(),"src/pages/AdminPanel.tsx"),"utf8");
 it("keeps global mutation and organization policy in distinct authority-gated tabs",()=>{
  expect(source).toContain('{isPlatformAdmin && <TabsTrigger value="documents"');
  expect(source).toContain('{isOrganizationAdmin && <TabsTrigger value="organization-documents"');
  expect(source).toContain('<DocumentDefinitionsTab />');
  expect(source).toContain('<OrganizationDocumentPolicyTab />');
  expect(source).not.toMatch(/isOrganizationAdmin[^\n]+<DocumentDefinitionsTab/);
 });
});
