import * as React from "react";

import { cn } from "@/lib/utils";

type LocalizedFileInputProps = Omit<React.ComponentProps<"input">, "type"> & {
  buttonLabel?: string;
  emptyLabel?: string;
  containerClassName?: string;
  selectedText?: string;
};

const LocalizedFileInput = React.forwardRef<HTMLInputElement, LocalizedFileInputProps>(
  (
    {
      id,
      buttonLabel,
      emptyLabel = "فایلی انتخاب نشده است",
      containerClassName,
      selectedText,
      className,
      multiple,
      disabled,
      onChange,
      ...props
    },
    ref,
  ) => {
    const generatedId = React.useId();
    const inputId = id || `file-${generatedId.replace(/:/g, "")}`;
    const [internalText, setInternalText] = React.useState(emptyLabel);
    const visibleText = selectedText ?? internalText;
    const label = buttonLabel || (multiple ? "انتخاب فایل‌ها" : "انتخاب فایل");

    return (
      <div className={cn("localized-file-picker", containerClassName)}>
        <input
          {...props}
          id={inputId}
          ref={ref}
          type="file"
          multiple={multiple}
          disabled={disabled}
          className={cn("localized-file-input", className)}
          onChange={(event) => {
            const files = Array.from(event.currentTarget.files || []);
            setInternalText(
              files.length > 1
                ? `${files.length.toLocaleString("fa-IR")} فایل انتخاب شده است`
                : files[0]?.name || emptyLabel,
            );
            onChange?.(event);
          }}
        />
        <div className={cn("localized-file-picker__control", disabled && "opacity-60")}>
          <label
            htmlFor={inputId}
            aria-disabled={disabled || undefined}
            className={cn("localized-file-picker__button", disabled ? "cursor-not-allowed" : "cursor-pointer")}
          >
            {label}
          </label>
          <span className="localized-file-picker__name" dir="auto" title={visibleText}>{visibleText}</span>
        </div>
      </div>
    );
  },
);

LocalizedFileInput.displayName = "LocalizedFileInput";

export { LocalizedFileInput };
