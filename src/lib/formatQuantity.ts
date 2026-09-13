/** Display only: preserve supplied significant decimals while hiding storage scale. */
export const formatQuantity = (value: string | number | null | undefined) => {
  if (value === null || value === undefined || value === "") return "0";
  const [integer, fraction] = String(value).split(".");
  const normalizedFraction = fraction?.replace(/0+$/, "");
  return `${Number(integer || 0).toLocaleString("en-US")}${normalizedFraction ? `.${normalizedFraction}` : ""}`;
};
