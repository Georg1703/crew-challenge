import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button, Sheet, TextField } from "@/shared/ui";

import styles from "../checkins.module.css";

/** "Another number": type how much to add when the quick chips do not fit. */
export function AmountSheet({
  unit,
  onClose,
  onAdd,
}: {
  unit: string;
  onClose: () => void;
  onAdd: (amount: number) => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string>();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const amount = Number(value.replace(",", "."));
    if (!(amount > 0) || amount > 1_000_000) {
      setError(t("checkins.amountError"));
      return;
    }
    onAdd(amount);
    onClose();
  };

  return (
    <Sheet open onClose={onClose} title={t("checkins.amountTitle")} closeLabel={t("common.close")}>
      <form onSubmit={submit} noValidate className={styles.actions}>
        <TextField
          label={t("checkins.amountLabel", { unit })}
          inputMode="decimal"
          autoFocus
          value={value}
          onChange={(event) => setValue(event.target.value)}
          error={error}
        />
        <Button type="submit" size="lg" fullWidth>
          {t("checkins.amountAdd")}
        </Button>
      </form>
    </Sheet>
  );
}
