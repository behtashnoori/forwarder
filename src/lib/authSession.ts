import { logoutExpert } from "./api";
import { clearExpertSession } from "./authContinuity";

export async function logoutAndClearExpertSession(): Promise<boolean> {
  const token = localStorage.getItem("expert_token");
  let serverConfirmed = false;
  try {
    if (token && token !== "null") serverConfirmed = await logoutExpert(token);
  } finally {
    clearExpertSession();
  }
  return serverConfirmed;
}
