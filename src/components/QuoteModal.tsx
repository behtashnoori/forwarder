import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";
import { submitQuote, type SubmitQuotePayload } from "@/lib/api";
import { formatQuantity, parseQuantityInput } from "@/lib/presentation";

interface QuoteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requestId: string;
  onSuccess: () => void;
}

const CURRENCY_OPTIONS = [
  { value: "IRR", label: "تومان (IRR)" },
  { value: "USD", label: "دلار (USD)" },
];

export function QuoteModal({ open, onOpenChange, requestId, onSuccess }: QuoteModalProps) {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("IRR");
  const [note, setNote] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const parsedAmount = parseQuantityInput(amount);
    // The existing API/DB quote contract is an integer amount. Do not round a
    // decimal entered by the user into a different commercial value.
    if (!parsedAmount || !/^\d+$/.test(parsedAmount.canonical)) {
      setError("مبلغ را به عدد وارد کنید");
      return;
    }
    setLoading(true);
    try {
      const payload: SubmitQuotePayload = {
        amount: parsedAmount.canonical,
        currency: currency || "IRR",
        note: note.trim() || undefined,
        valid_until: validUntil.trim() || undefined,
      };
      await submitQuote(requestId, payload);
      onSuccess();
      onOpenChange(false);
      setAmount("");
      setNote("");
      setValidUntil("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "خطا در ثبت پیشنهاد";
      if (message.includes("Invalid token") || message.includes("Token") || message.includes("token")) {
        localStorage.removeItem("expert_token");
        localStorage.removeItem("expert_user");
        setError("نشست شما منقضی شده است. لطفاً دوباره وارد شوید.");
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>ارسال پیشنهاد</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</p>
          )}
          <div className="space-y-2">
            <Label htmlFor="quote-amount">مبلغ (الزامی)</Label>
            <Input
              id="quote-amount"
              type="text"
              inputMode="numeric"
              placeholder="مثال: 1,500,000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onBlur={() => {
                const parsed = parseQuantityInput(amount);
                if (parsed && /^\d+$/.test(parsed.canonical)) setAmount(formatQuantity(parsed.canonical, "en-US"));
              }}
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="quote-currency">ارز</Label>
            <select
              id="quote-currency"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              disabled={loading}
            >
              {CURRENCY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="quote-note">توضیح کوتاه (اختیاری)</Label>
            <Textarea
              id="quote-note"
              placeholder="توضیحات پیشنهاد"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="resize-none"
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="quote-valid">تاریخ اعتبار (اختیاری)</Label>
            <Input
              id="quote-valid"
              type="date"
              value={validUntil}
              onChange={(e) => setValidUntil(e.target.value)}
              disabled={loading}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              انصراف
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <Loader2 className="w-4 h-4 ml-2 animate-spin" />
              ) : null}
              ارسال پیشنهاد
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
