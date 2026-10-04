import { create } from "qrcode";
import { useMemo } from "react";

import styles from "./QrCode.module.css";

/** A QR code for `value`, drawn as one SVG path. Dark on white in both themes. */
export function QrCode({ value, label }: { value: string; label: string }) {
  const { size, path } = useMemo(() => {
    const { modules } = create(value, { errorCorrectionLevel: "M" });
    let d = "";
    for (let row = 0; row < modules.size; row++) {
      for (let col = 0; col < modules.size; col++) {
        if (modules.get(row, col)) d += `M${col} ${row}h1v1h-1z`;
      }
    }
    return { size: modules.size, path: d };
  }, [value]);

  return (
    <div className={styles.frame}>
      <svg
        className={styles.code}
        viewBox={`-2 -2 ${size + 4} ${size + 4}`}
        role="img"
        aria-label={label}
        shapeRendering="crispEdges"
      >
        <path d={path} />
      </svg>
    </div>
  );
}
