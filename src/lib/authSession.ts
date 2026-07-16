import { logoutExpert } from "./api";

export async function logoutAndClearExpertSession(): Promise<boolean> {
  const token = localStorage.getItem("expert_token");
  let serverConfirmed = false;
  try {
    if (token && token !== "null") serverConfirmed = await logoutExpert(token);
  } finally {
    localStorage.removeItem("expert_user");
    localStorage.removeItem("expert_token");
  }
  return serverConfirmed;
}
