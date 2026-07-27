# Permission matrix

| Operation | Permission |
|---|---|
| Read plans/timeline | `route_plan.read` |
| Create draft | `route_plan.create` |
| Activate | `route_plan.activate` |
| Replan | `route_plan.replan` |
| Manage legs | `route_leg.manage` |
| Report checkpoint | `checkpoint.report` |
| Verify checkpoint | `checkpoint.verify` |
| Read/manage exceptions | `route_exception.read` / `route_exception.manage` |

Every query additionally enforces the caller's single active operational organization.
