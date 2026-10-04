import { useState } from "react";

import { useInstallPrompt } from "./installPrompt";
import { IosInstallGuide } from "./IosInstallGuide";
import { detectPlatform } from "./platform";

/**
 * 1.5 Install the app, as one step of a flow. `begin(done)` opens the iOS guide (done runs when
 * it closes) or the browser's install dialog; when the app cannot be installed, or is already
 * installed, it calls `done` straight away. Render `guide` once in the screen.
 */
export function useInstallStep() {
  const { canPrompt, justInstalled, prompt } = useInstallPrompt();
  const [platform] = useState(detectPlatform);
  const [onDone, setOnDone] = useState<(() => void) | null>(null);

  const begin = (done: () => void) => {
    if (platform.standalone || justInstalled) return done();
    if (platform.ios) return setOnDone(() => done);
    if (canPrompt) return void prompt().finally(done);
    done();
  };

  const close = () => {
    onDone?.();
    setOnDone(null);
  };

  return {
    begin,
    guide: platform.ios ? <IosInstallGuide open={onDone !== null} onClose={close} /> : null,
  };
}
