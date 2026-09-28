const absentCargoDescriptions = new Set(["ندارد", "ندارد.", "-", "—"]);

export const meaningfulCargoDescription = (value: string | null | undefined): string | null => {
  const normalized = value?.trim();
  if (!normalized || absentCargoDescriptions.has(normalized)) return null;
  return normalized;
};
